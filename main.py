"""Pipes Puzzle dashboard powered by Greedy Best-First Search."""
from __future__ import annotations

import json
import os
import queue
import random
import sys
import threading
import time
from typing import Optional

import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from generator import make_random_puzzle
from puzzle import PipesPuzzle
from search import SearchResult, SearchTraceStep, greedy_best_first

BOARD_W = 560
HEADER_H = 164
BOARD_MARGIN = 24
CARD_H = 605
PANEL_W = 552
GAP = 18
FPS = 60
MAX_NODES = 500_000
MAX_TRACE_STEPS = 2_000
PLAYBACK_DELAYS = (1.6, 0.8, 0.4, 0.16)
GRID_AREA_TOP = 112
GRID_AREA_BOTTOM = 56
MIN_CELL = 64
MAX_CELL = 110

THEME_DARK = {
    "bg": (10, 17, 31),
    "header": (15, 25, 44),
    "board": (18, 29, 49),
    "card": (22, 35, 57),
    "card_alt": (28, 44, 70),
    "cell": (30, 48, 75),
    "cell_hover": (48, 69, 103),
    "cell_locked": (39, 47, 68),
    "border": (49, 71, 104),
    "text": (236, 243, 255),
    "muted": (145, 162, 190),
    "faint": (91, 112, 144),
    "accent": (106, 153, 255),
    "accent_dark": (42, 71, 129),
    "green": (71, 222, 165),
    "red": (255, 116, 135),
    "source": (255, 88, 92),
    "yellow": (255, 201, 91),
    "white": (255, 255, 255),
}
THEME_AURORA = {
    **THEME_DARK,
    "bg": (13, 18, 37),
    "header": (22, 24, 55),
    "board": (24, 29, 61),
    "card": (30, 35, 72),
    "card_alt": (40, 46, 88),
    "cell": (37, 48, 88),
    "cell_hover": (62, 73, 126),
    "border": (71, 86, 143),
    "accent": (146, 133, 255),
    "accent_dark": (75, 65, 151),
    "green": (69, 224, 190),
}
COLORS = dict(THEME_DARK)

PUZZLE_FILES = {
    "1": os.path.join(BASE_DIR, "puzzles", "tiny_3x3.json"),
    "2": os.path.join(BASE_DIR, "puzzles", "easy_4x4.json"),
    "3": os.path.join(BASE_DIR, "puzzles", "medium_5x5.json"),
    "4": os.path.join(BASE_DIR, "puzzles", "hard_6x6.json"),
}
PUZZLE_LABELS = {
    "1": ("TINY", "3 x 3"),
    "2": ("EASY", "4 x 4"),
    "3": ("MEDIUM", "5 x 5"),
    "4": ("HARD", "6 x 6"),
}
PUZZLE_SIZES = {
    "1": (3, 3),
    "2": (4, 4),
    "3": (5, 5),
    "4": (6, 6),
}
PUZZLE_NAMES = {
    "1": "M\u1ea1ng nh\u1ecf",
    "2": "M\u1ea1ng c\u01a1 b\u1ea3n",
    "3": "M\u1ea1ng nhi\u1ec1u nh\u00e1nh",
    "4": "M\u1ea1ng nhi\u1ec1u v\u00f2ng",
}
DIRS = [(-1, 0), (0, 1), (1, 0), (0, -1)]
OPPOSITE = [2, 3, 0, 1]


def load_puzzle(path: str) -> PipesPuzzle:
    with open(path, "r", encoding="utf-8") as file:
        return PipesPuzzle.from_dict(json.load(file))


def cell_is_bad(puzzle: PipesPuzzle, state: tuple[int, ...], idx: int) -> bool:
    row, col = puzzle.rc(idx)
    connections = set(puzzle.get_connections(state, idx))
    for direction, (dr, dc) in enumerate(DIRS):
        nr, nc = row + dr, col + dc
        neighbour_open = False
        if 0 <= nr < puzzle.rows and 0 <= nc < puzzle.cols:
            neighbour = puzzle.idx(nr, nc)
            neighbour_open = OPPOSITE[direction] in puzzle.get_connections(state, neighbour)
        if (direction in connections) != neighbour_open:
            return True
    return False


class App:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Pipes Puzzle | Greedy Best-First Search")
        self.font = pygame.font.SysFont("segoeui", 17)
        self.font_small = pygame.font.SysFont("segoeui", 14)
        self.font_tiny = pygame.font.SysFont("segoeui", 12)
        self.font_bold = pygame.font.SysFont("segoeui", 19, bold=True)
        self.font_title = pygame.font.SysFont("segoeui", 32, bold=True)
        self.font_number = pygame.font.SysFont("segoeui", 24, bold=True)

        self.puzzle_key = "1"
        self.puzzle = load_puzzle(PUZZLE_FILES[self.puzzle_key])
        self.state = self.puzzle.initial_state()
        self.solution_state: Optional[tuple[int, ...]] = None
        self.seed_value = 42
        self.previous_state: Optional[tuple[int, ...]] = None
        self.theme_alt = False
        # Sparse is the default so new boards start with fewer pre-connected edges.
        self.sparse_mode = True

        self.search_result: Optional[SearchResult] = None
        self.search_path: list[tuple[int, ...]] = []
        self.search_step = 0
        self.search_running = False
        self.search_paused = False
        self.search_computing = False
        self.search_worker: Optional[threading.Thread] = None
        self.search_pending_result: Optional[SearchResult] = None
        self.search_cancel_requested = False
        self.search_token = 0
        self.search_started_at = 0.0
        self.pending_traces: queue.SimpleQueue[tuple[int, SearchTraceStep]] = queue.SimpleQueue()
        self.trace_steps: list[SearchTraceStep] = []
        self.trace_index = 0
        self.view_mode = "trace"
        self.candidate_scroll = 0
        self.candidate_rect = pygame.Rect(0, 0, 0, 0)
        self.timeline_rect = pygame.Rect(0, 0, 0, 0)
        self.timeline_dragging = False
        self.inspector_buttons: dict[str, pygame.Rect] = {}
        self.speed_index = 1
        self.search_start_state = self.state
        self.live_stats = {"expanded": 0, "generated": 1, "frontier": 1, "max_frontier": 1}
        self.solved = self.puzzle.is_goal(self.state)
        self.status = "SOLVED" if self.solved else "READY"
        self.status_detail = "T\u1ef1 xoay c\u00e1c \u00f4 ho\u1eb7c nh\u1ea5n G \u0111\u1ec3 Greedy t\u00ecm l\u1eddi gi\u1ea3i."
        self.auto_delay = PLAYBACK_DELAYS[self.speed_index]
        self.last_step_time = time.perf_counter()

        self.puzzle_buttons: dict[str, pygame.Rect] = {}
        self.header_buttons: dict[str, pygame.Rect] = {}
        self.action_buttons: dict[str, pygame.Rect] = {}
        self._resize()
        self.clock = pygame.time.Clock()
        self.new_puzzle()

    @property
    def board_size(self) -> int:
        return self.puzzle.cols * self.cell_size

    @property
    def cell_size(self) -> int:
        """Choose a readable tile size for each board size."""
        available_width = BOARD_W - 80
        available_height = CARD_H - GRID_AREA_TOP - GRID_AREA_BOTTOM
        size = min(
            available_width // self.puzzle.cols,
            available_height // self.puzzle.rows,
            MAX_CELL,
        )
        return max(MIN_CELL, size)

    @property
    def panel_x(self) -> int:
        return BOARD_MARGIN + BOARD_W + GAP

    @property
    def grid_left(self) -> int:
        return BOARD_MARGIN + (BOARD_W - self.board_size) // 2

    @property
    def board_top(self) -> int:
        return HEADER_H + 12

    @property
    def grid_top(self) -> int:
        available_height = CARD_H - GRID_AREA_TOP - GRID_AREA_BOTTOM
        return self.board_top + GRID_AREA_TOP + (available_height - self.board_size) // 2

    def _resize(self) -> None:
        width = max(1162, BOARD_MARGIN * 2 + BOARD_W + GAP + PANEL_W)
        height = max(840, self.grid_top + self.board_size + 105)
        self.screen = pygame.display.set_mode((width, height))

    def _invalidate_search(self) -> None:
        """Stop a running worker and invalidate any result it may return."""
        self.search_token += 1
        self.search_cancel_requested = True
        self.search_computing = False
        self.search_pending_result = None
        self.search_running = False
        self.search_paused = False
        self._clear_search()

    def reset(self) -> None:
        """Reset the current generated layout without changing its seed."""
        self._invalidate_search()
        self.state = self.puzzle.initial_state()
        self.previous_state = None
        self.solved = self.puzzle.is_goal(self.state)
        self.status = "SOLVED" if self.solved else "READY"
        self.status_detail = "T\u1ef1 xoay c\u00e1c \u00f4 ho\u1eb7c nh\u1ea5n G \u0111\u1ec3 Greedy t\u00ecm l\u1eddi gi\u1ea3i."
        self._resize()

    def new_puzzle(self) -> None:
        """Generate a new solvable network for the selected size and mode."""
        self._invalidate_search()
        rows, cols = PUZZLE_SIZES[self.puzzle_key]
        self.seed_value = random.SystemRandom().randrange(100_000, 1_000_000)
        self.puzzle, self.solution_state = make_random_puzzle(
            rows,
            cols,
            seed=self.seed_value,
            sparse=self.sparse_mode,
        )
        self.state = self.puzzle.initial_state()
        self.previous_state = None
        self.solved = self.puzzle.is_goal(self.state)
        self.status = "READY"
        self.status_detail = "B\u00e0i to\u00e1n m\u1edbi \u0111\u00e3 s\u1eb5n s\u00e0ng \u0111\u1ec3 kh\u00e1m ph\u00e1."
        self._resize()

    def toggle_theme(self) -> None:
        self.theme_alt = not self.theme_alt
        COLORS.update(THEME_AURORA if self.theme_alt else THEME_DARK)
        self.status_detail = "Đã bật bảng màu Aurora." if self.theme_alt else "Đã bật bảng màu Midnight."

    def toggle_mode(self) -> None:
        """Switch between loop-rich and tree-like generated networks."""
        self.sparse_mode = not self.sparse_mode
        self.new_puzzle()

    def switch_puzzle(self, key: str) -> None:
        if key in PUZZLE_SIZES:
            self.puzzle_key = key
            self.new_puzzle()

    def _clear_search(self) -> None:
        self.search_result = None
        self.search_path = []
        self.search_step = 0
        self.search_running = False
        self.search_paused = False
        self.trace_steps = []
        self.trace_index = 0
        self.candidate_scroll = 0
        self.view_mode = "trace"
        self.timeline_dragging = False

    def cancel_search(self) -> None:
        if not (self.search_computing or self.search_running):
            return
        if self.search_computing:
            self.search_cancel_requested = True
        self.search_running = False
        self.search_paused = True
        self.status = "CANCELLED"
        self.status_detail = "Đã dừng. Bạn vẫn có thể xem lại các bước đã ghi."

    def on_board_click(self, position: tuple[int, int]) -> None:
        if self.search_running or self.search_computing or self.trace_steps or self.search_path:
            return
        x, y = position
        col = (x - self.grid_left) // self.cell_size
        row = (y - self.grid_top) // self.cell_size
        if not (0 <= row < self.puzzle.rows and 0 <= col < self.puzzle.cols):
            return
        idx = self.puzzle.idx(row, col)
        cell = self.puzzle.cells[idx]
        if cell.locked or cell.type in ("EMPTY", "CROSS"):
            return
        state = list(self.state)
        state[idx] = (state[idx] + 1) % 4
        self.previous_state = self.state
        self.state = tuple(state)
        self._clear_search()
        self.solved = self.puzzle.is_goal(self.state)
        self.status = "SOLVED" if self.solved else "MANUAL"
        self.status_detail = "M\u1ea1ng \u1ed1ng \u0111\u00e3 ho\u00e0n ch\u1ec9nh." if self.solved else "T\u1ef1 xoay c\u00e1c \u00f4 ho\u1eb7c nh\u1ea5n G \u0111\u1ec3 t\u00ecm l\u1eddi gi\u1ea3i."

    def _on_search_progress(self, token: int, state: tuple[int, ...], expanded: int, generated: int, frontier: int) -> None:
        if token != self.search_token or self.search_cancel_requested:
            return
        self.live_stats = {
            "expanded": expanded,
            "generated": generated,
            "frontier": frontier,
            "max_frontier": max(self.live_stats.get("max_frontier", 1), frontier),
        }

    def _search_worker(self, token: int, puzzle: PipesPuzzle, start_state: tuple[int, ...]) -> None:
        result = greedy_best_first(
            puzzle,
            max_nodes=MAX_NODES,
            start_state=start_state,
            progress_callback=lambda state, expanded, generated, frontier: self._on_search_progress(
                token, state, expanded, generated, frontier
            ),
            cancel_check=lambda: token != self.search_token or self.search_cancel_requested,
            trace_callback=lambda step: self.pending_traces.put((token, step)),
            trace_limit=MAX_TRACE_STEPS,
        )
        if token == self.search_token:
            self.search_pending_result = result

    def _finish_search(self, result: SearchResult) -> None:
        self.search_result = result
        self.search_path = result.path
        self.search_step = 0
        self.search_cancel_requested = False
        if result.found:
            self.status = "REVIEW"
            self.status_detail = f"Đã tìm thấy lời giải: {result.depth} lần xoay. Xem từng bước AI bên dưới."
        elif result.termination_reason == "cancelled":
            self.status = "CANCELLED"
            self.status_detail = "Đã hủy tìm kiếm. Các bước đã ghi vẫn có thể xem lại."
        else:
            self.status = "NO SOLUTION"
            reason = "Đã chạm giới hạn số trạng thái" if result.termination_reason == "node_limit" else "Đã xét hết hàng đợi"
            self.status_detail = f"{reason}; chưa tìm thấy lời giải."

    def run_greedy(self) -> None:
        if self.search_computing or (self.search_worker is not None and self.search_worker.is_alive()):
            return
        start_state = self.search_start_state if self.trace_steps or self.search_path else self.state
        self._clear_search()
        self.state = start_state
        self.previous_state = None
        self.search_start_state = start_state
        self.status = "SEARCHING"
        self.status_detail = "Đang ghi các bước chọn trạng thái, sinh nhánh và cập nhật hàng đợi."
        self.solved = False
        self.search_paused = True
        self.search_cancel_requested = False
        self.search_pending_result = None
        self.search_token += 1
        token = self.search_token
        self.search_computing = True
        self.search_started_at = time.perf_counter()
        self.live_stats = {"expanded": 0, "generated": 1, "frontier": 1, "max_frontier": 1}
        working_puzzle = PipesPuzzle(
            self.puzzle.rows, self.puzzle.cols, self.puzzle.cells,
            root_index=self.puzzle.root_index,
        )
        self.search_worker = threading.Thread(
            target=self._search_worker,
            args=(token, working_puzzle, start_state),
            name="greedy-search", daemon=True,
        )
        self.search_worker.start()

    @property
    def playback_length(self) -> int:
        return len(self.trace_steps) if self.view_mode == "trace" else len(self.search_path)

    @property
    def playback_index(self) -> int:
        return self.trace_index if self.view_mode == "trace" else self.search_step

    @property
    def current_trace(self) -> Optional[SearchTraceStep]:
        return self.trace_steps[self.trace_index] if self.trace_steps else None

    def select_step(self, index: int, pause: bool = True) -> None:
        if not self.playback_length:
            return
        index = max(0, min(index, self.playback_length - 1))
        if pause:
            self.search_running = False
            self.search_paused = True
        if self.view_mode == "trace":
            self.trace_index = index
            step = self.trace_steps[index]
            # Consecutive expanded nodes can belong to different search branches.
            # Highlight the move from this node's actual parent instead.
            self.previous_state = step.parent_state
            self.state = step.state
        else:
            self.search_step = index
            self.previous_state = self.search_path[index - 1] if index else None
            self.state = self.search_path[index]
        self.candidate_scroll = 0
        self.solved = self.puzzle.is_goal(self.state)
        self.last_step_time = time.perf_counter()

    def set_view(self, mode: str) -> None:
        if mode == "solution" and not self.search_path:
            return
        self.view_mode = mode
        self.select_step(self.playback_index)

    def step_search(self, direction: int = 1) -> None:
        if not self.playback_length:
            if not self.search_computing:
                self.run_greedy()
            return
        self.select_step(self.playback_index + direction)

    def toggle_pause(self) -> None:
        if not self.playback_length:
            return
        if self.search_running:
            self.search_running = False
            self.search_paused = True
        else:
            if self.playback_index == self.playback_length - 1:
                self.select_step(0)
            self.search_running = True
            self.search_paused = False
        self.last_step_time = time.perf_counter()

    def cycle_speed(self) -> None:
        self.speed_index = (self.speed_index + 1) % len(PLAYBACK_DELAYS)
        self.auto_delay = PLAYBACK_DELAYS[self.speed_index]
        self.last_step_time = time.perf_counter()

    def seek_timeline(self, x: int) -> None:
        if self.playback_length:
            fraction = max(0.0, min(1.0, (x - self.timeline_rect.x) / self.timeline_rect.width))
            self.select_step(round(fraction * (self.playback_length - 1)))

    def update(self) -> None:
        # Queue messages are tagged so resets/new puzzles cannot receive old traces.
        for _ in range(256):
            try:
                token, step = self.pending_traces.get_nowait()
            except queue.Empty:
                break
            if token == self.search_token:
                self.trace_steps.append(step)
                if len(self.trace_steps) == 1 and self.view_mode == "trace":
                    self.select_step(0)

        if self.search_computing and self.search_pending_result is not None and self.pending_traces.empty():
            result = self.search_pending_result
            self.search_pending_result = None
            self.search_computing = False
            self._finish_search(result)
        elif self.search_computing and self.search_worker is not None and not self.search_worker.is_alive() and self.search_pending_result is None:
            self.search_computing = False
            self.search_running = False
            self.search_paused = True
            self.status = "ERROR"
            self.status_detail = "Tìm kiếm đã dừng do lỗi. Nhấn G để thử lại; bản ghi đã có vẫn xem được."

        if self.search_running and self.playback_length:
            if time.perf_counter() - self.last_step_time >= self.auto_delay:
                if self.playback_index < self.playback_length - 1:
                    self.select_step(self.playback_index + 1, pause=False)
                elif not self.search_computing:
                    self.search_running = False
                    self.search_paused = True

    def describe_action(self, action: str) -> str:
        if not action:
            return "Trạng thái ban đầu"
        cell, turns = action[1:].split("+")
        row, col = self.puzzle.rc(int(cell))
        return f"Ô ({row + 1}, {col + 1}) xoay {int(turns) * 90}°"

    def draw_text(self, text: str, position: tuple[int, int], color=None, font=None) -> None:
        self.screen.blit((font or self.font).render(text, True, color or COLORS["text"]), position)

    def draw_wrapped_text(
        self,
        text: str,
        position: tuple[int, int],
        max_width: int,
        color=None,
        font=None,
        max_lines: int = 2,
    ) -> None:
        """Render short UI messages without clipping their ending."""
        active_font = font or self.font
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and active_font.size(candidate)[0] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            while last and active_font.size(f"{last}...")[0] > max_width:
                last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
            lines[-1] = f"{last}..."
        line_height = active_font.get_linesize()
        for index, line in enumerate(lines):
            self.draw_text(line, (position[0], position[1] + index * line_height), color, active_font)

    def draw_panel(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, COLORS["card"], rect, border_radius=18)
        pygame.draw.rect(self.screen, COLORS["border"], rect, width=1, border_radius=18)

    def draw(self) -> None:
        self.screen.fill(COLORS["bg"])
        self.draw_header()
        self.draw_board()
        self.draw_sidebar()
        self.draw_footer()
        pygame.display.flip()

    def draw_header(self) -> None:
        pygame.draw.rect(self.screen, COLORS["header"], (0, 0, self.screen.get_width(), HEADER_H))
        for x in range(18, self.screen.get_width(), 48):
            for y in range(18, HEADER_H, 34):
                pygame.draw.circle(self.screen, COLORS["card_alt"], (x, y), 1)
        self.draw_text("PIPES", (BOARD_MARGIN, 18), COLORS["text"], self.font_title)
        badge = pygame.Rect(174, 30, 142, 31)
        pygame.draw.rect(self.screen, COLORS["card_alt"], badge, border_radius=9)
        self.draw_text("GREEDY SEARCH", (badge.x + 19, badge.y + 8), COLORS["accent"], self.font_tiny)
        self.draw_text("Theo dõi cách Greedy chọn trạng thái và tìm lời giải.", (BOARD_MARGIN + 2, 66), COLORS["muted"], self.font_small)

        self.header_buttons = {}
        new_rect = pygame.Rect(self.screen.get_width() - 334, 27, 150, 45)
        mode_rect = pygame.Rect(self.screen.get_width() - 174, 27, 88, 45)
        theme_rect = pygame.Rect(self.screen.get_width() - 80, 27, 56, 45)
        self.header_buttons["new"] = new_rect
        self.header_buttons["mode"] = mode_rect
        self.header_buttons["theme"] = theme_rect
        self.draw_button(new_rect, "BÀI TOÁN MỚI", "N", primary=True)
        self.draw_button(mode_rect, "SPARSE" if self.sparse_mode else "DENSE", "M")
        self.draw_button(theme_rect, "MÀU", "T")
        mode_name = "Sparse / ít nhánh" if self.sparse_mode else "Dense / nhiều nhánh"
        palette_name = "Aurora" if self.theme_alt else "Midnight"
        self.draw_text(f"{palette_name} · {mode_name}", (self.screen.get_width() - 334, 82), COLORS["faint"], self.font_tiny)

        tab_y = 113
        tab_gap = 10
        tab_w = (self.screen.get_width() - 2 * BOARD_MARGIN - 3 * tab_gap) // 4
        self.puzzle_buttons = {}
        for i, key in enumerate(("1", "2", "3", "4")):
            rect = pygame.Rect(BOARD_MARGIN + i * (tab_w + tab_gap), tab_y, tab_w, 40)
            self.puzzle_buttons[key] = rect
            label, size = PUZZLE_LABELS[key]
            active = key == self.puzzle_key
            fill = COLORS["accent_dark"] if active else COLORS["card_alt"]
            pygame.draw.rect(self.screen, fill, rect, border_radius=11)
            if active:
                pygame.draw.rect(self.screen, COLORS["accent"], rect, width=1, border_radius=11)
            self.draw_text(f"[{key}]  {label}  ·  {size}", (rect.x + 27, rect.y + 11), COLORS["text"], self.font)

    def draw_board(self) -> None:
        grid_left = self.grid_left
        grid_top = self.grid_top
        cell_size = self.cell_size
        board_rect = pygame.Rect(BOARD_MARGIN, self.board_top, BOARD_W, CARD_H)
        self.draw_panel(board_rect)
        mode_name = "SPARSE" if self.sparse_mode else "DENSE"
        board_name = "Mạng thưa" if self.sparse_mode else PUZZLE_NAMES[self.puzzle_key]
        title = f"{self.puzzle.cols} x {self.puzzle.rows}  /  {board_name}  ·  {mode_name}"
        self.draw_text(title, (BOARD_MARGIN + 14, self.board_top + 20), COLORS["text"], self.font_bold)
        board_hint = "Viền vàng: ô xoay từ trạng thái cha  |  R: về chơi thủ công" if self.trace_steps or self.search_path else "Xanh: nối khớp  |  Đỏ: lỗi kết nối  |  Click ô để xoay"
        self.draw_text(board_hint, (BOARD_MARGIN + 14, self.board_top + 49), COLORS["muted"], self.font_tiny)
        pill = pygame.Rect(BOARD_MARGIN + BOARD_W - 130, self.board_top + 18, 116, 27)
        pygame.draw.rect(self.screen, COLORS["card_alt"], pill, border_radius=12)
        self.draw_text(f"h={self.puzzle.heuristic(self.state)}  ·  {self.puzzle.count_mismatches(self.state)} lỗi", (pill.x + 10, pill.y + 7), COLORS["accent"], self.font_tiny)

        if self.trace_steps or self.search_path:
            caption = f"Đang xét node #{self.current_trace.node_id}" if self.view_mode == "trace" and self.current_trace else f"Lời giải · lần xoay {self.search_step}"
            self.draw_text(caption, (BOARD_MARGIN + 14, self.board_top + 72), COLORS["accent"], self.font_tiny)
        for col in range(self.puzzle.cols):
            self.draw_text(str(col + 1), (grid_left + col * cell_size + cell_size // 2 - 4, grid_top - 20), COLORS["faint"], self.font_tiny)
        for row in range(self.puzzle.rows):
            self.draw_text(str(row + 1), (grid_left - 19, grid_top + row * cell_size + cell_size // 2 - 8), COLORS["faint"], self.font_tiny)

        changed = set()
        if self.previous_state is not None:
            changed = {i for i, (a, b) in enumerate(zip(self.previous_state, self.state)) if a != b}
        mouse_x, mouse_y = pygame.mouse.get_pos()
        hovered_idx: Optional[int] = None
        if grid_left <= mouse_x < grid_left + self.board_size and grid_top <= mouse_y < grid_top + self.board_size:
            hover_col = (mouse_x - grid_left) // cell_size
            hover_row = (mouse_y - grid_top) // cell_size
            if 0 <= hover_row < self.puzzle.rows and 0 <= hover_col < self.puzzle.cols:
                hovered_idx = self.puzzle.idx(hover_row, hover_col)
        for row in range(self.puzzle.rows):
            for col in range(self.puzzle.cols):
                idx = self.puzzle.idx(row, col)
                cell = self.puzzle.cells[idx]
                x = grid_left + col * cell_size
                y = grid_top + row * cell_size
                inset = max(3, cell_size // 24)
                rect = pygame.Rect(x + inset, y + inset, cell_size - 2 * inset, cell_size - 2 * inset)
                bad = cell_is_bad(self.puzzle, self.state, idx)
                if cell.locked:
                    fill = COLORS["cell_locked"]
                elif idx in changed:
                    fill = COLORS["cell_hover"]
                elif hovered_idx == idx:
                    fill = COLORS["cell_hover"]
                elif bad:
                    fill = (66, 42, 68)
                else:
                    fill = COLORS["cell"]
                pygame.draw.rect(self.screen, fill, rect, border_radius=12)
                pygame.draw.rect(self.screen, COLORS["border"], rect, width=1, border_radius=12)
                if idx in changed:
                    pygame.draw.rect(self.screen, COLORS["yellow"], rect, width=2, border_radius=12)
                self.draw_pipe(x, y, idx, bad)
                if cell.locked and idx != self.puzzle.root_index:
                    pygame.draw.circle(self.screen, COLORS["yellow"], (rect.right - 13, rect.top + 13), 4)
                    self.draw_text("L", (rect.right - 22, rect.top + 7), COLORS["yellow"], self.font_tiny)
                if idx == self.puzzle.root_index:
                    pygame.draw.circle(self.screen, COLORS["source"], (rect.right - 13, rect.top + 13), 5)
                    self.draw_text("G", (rect.right - 22, rect.top + 7), COLORS["source"], self.font_tiny)

        legend_y = board_rect.bottom - 45
        legend_items = [
            ("N\u1ed1i kh\u1edbp", COLORS["green"]),
            ("L\u1ed7i k\u1ebft n\u1ed1i", COLORS["red"]),
            ("G\u1ed1c ngu\u1ed3n", COLORS["source"]),
            ("Ô vừa xoay", COLORS["yellow"]),
        ]
        for index, (label, color) in enumerate(legend_items):
            x = BOARD_MARGIN + 20 + index * 132
            self.draw_text("\u25cf", (x, legend_y), color, self.font_small)
            self.draw_text(label, (x + 14, legend_y + 2), COLORS["muted"], self.font_tiny)

    def draw_pipe(self, x: int, y: int, idx: int, bad: bool) -> None:
        connections = self.puzzle.get_connections(self.state, idx)
        cell_size = self.cell_size
        center = (x + cell_size // 2, y + cell_size // 2)
        endpoint_pad = max(8, int(cell_size * 0.11))
        line_width = max(8, int(cell_size * 0.12))
        endpoint_radius = max(4, int(cell_size * 0.055))
        center_radius = max(9, int(cell_size * 0.12))
        center_hole_radius = max(4, int(cell_size * 0.055))
        if not connections:
            pygame.draw.circle(self.screen, COLORS["faint"], center, 4)
            return
        row, col = self.puzzle.rc(idx)
        for direction in connections:
            dr, dc = DIRS[direction]
            nr, nc = row + dr, col + dc
            arm_bad = not (0 <= nr < self.puzzle.rows and 0 <= nc < self.puzzle.cols)
            if not arm_bad:
                neighbour = self.puzzle.idx(nr, nc)
                arm_bad = OPPOSITE[direction] not in self.puzzle.get_connections(self.state, neighbour)
            end = list(center)
            if direction == 0:
                end[1] = y + endpoint_pad
            elif direction == 1:
                end[0] = x + cell_size - endpoint_pad
            elif direction == 2:
                end[1] = y + cell_size - endpoint_pad
            else:
                end[0] = x + endpoint_pad
            color = COLORS["red"] if arm_bad else COLORS["green"]
            pygame.draw.line(self.screen, color, center, tuple(end), line_width)
            pygame.draw.circle(self.screen, color, tuple(end), endpoint_radius)
        pygame.draw.circle(self.screen, COLORS["red"] if bad else COLORS["green"], center, center_radius)
        pygame.draw.circle(self.screen, COLORS["cell"], center, center_hole_radius)

    def draw_button(self, rect: pygame.Rect, label: str, key: str = "", primary: bool = False, disabled: bool = False) -> None:
        hover = rect.collidepoint(pygame.mouse.get_pos()) and not disabled
        if disabled:
            fill, color = COLORS["card_alt"], COLORS["faint"]
        elif primary:
            fill, color = (COLORS["accent"] if not hover else (133, 177, 255)), COLORS["bg"]
        else:
            fill, color = (COLORS["card_alt"] if not hover else COLORS["cell_hover"]), COLORS["text"]
        pygame.draw.rect(self.screen, fill, rect, border_radius=11)
        pygame.draw.rect(self.screen, COLORS["border"], rect, width=1, border_radius=11)
        caption = f"[{key}]  {label}" if key else label
        rendered = self.font_small.render(caption, True, color)
        self.screen.blit(rendered, rendered.get_rect(center=rect.center))

    def draw_sidebar(self) -> None:
        x, y = self.panel_x, self.board_top
        width = PANEL_W - 40
        self.draw_panel(pygame.Rect(x, y, PANEL_W, CARD_H))
        self.inspector_buttons = {}
        self.action_buttons = {}
        for index, (mode, label) in enumerate((("trace", "QUÁ TRÌNH TÌM KIẾM"), ("solution", "ĐƯỜNG ĐI LỜI GIẢI"))):
            rect = pygame.Rect(x + 20 + index * (width // 2 + 4), y + 14, width // 2 - 4, 32)
            self.inspector_buttons[mode] = rect
            self.draw_button(rect, label, primary=self.view_mode == mode, disabled=mode == "solution" and not self.search_path)
        self.draw_wrapped_text(self.status_detail, (x + 20, y + 54), width, COLORS["accent"] if self.search_computing else COLORS["muted"], self.font_tiny)

        controls = [
            ("run", "Đang tìm…" if self.search_computing else "Chạy AI [G]", 111),
            ("back", "Lùi", 49), ("step", "Tiến", 49),
            ("pause", "Dừng" if self.search_running else "Phát", 60),
            ("speed", ("0.5x", "1x", "2x", "5x")[self.speed_index], 47),
            ("reset", "Reset", 65), ("cancel", "Hủy", 65),
        ]
        cx = x + 20
        for name, label, button_width in controls:
            rect = pygame.Rect(cx, y + 94, button_width, 34)
            self.action_buttons[name] = rect
            disabled = ((name == "run" and self.search_computing)
                        or (name in ("back", "pause") and not self.playback_length)
                        or (name == "back" and self.playback_index == 0)
                        or (name == "step" and self.playback_length > 0 and self.playback_index == self.playback_length - 1)
                        or (name == "cancel" and not (self.search_computing or self.search_running)))
            self.draw_button(rect, label, primary=name == "run", disabled=disabled)
            cx += button_width + 6

        self.timeline_rect = pygame.Rect(x + 24, y + 141, width - 8, 12)
        pygame.draw.rect(self.screen, COLORS["card_alt"], self.timeline_rect, border_radius=6)
        progress = self.playback_index / max(1, self.playback_length - 1)
        knob_x = self.timeline_rect.x + round(progress * self.timeline_rect.width)
        pygame.draw.line(self.screen, COLORS["accent"], self.timeline_rect.midleft, (knob_x, self.timeline_rect.centery), 4)
        pygame.draw.circle(self.screen, COLORS["accent"], (knob_x, self.timeline_rect.centery), 6)
        step = self.current_trace
        if self.view_mode == "trace":
            label = f"Lượt mở rộng {step.number:,}  ·  Bản ghi {self.trace_index + 1}/{len(self.trace_steps)}" if step else "Chưa có bước tìm kiếm"
        else:
            label = f"Lần xoay {self.search_step}/{max(0, len(self.search_path) - 1)}"
        self.draw_text(label, (x + 20, y + 158), COLORS["muted"], self.font_tiny)

        if self.view_mode == "trace" and step is not None:
            self.draw_trace_details(step, x, y)
        elif self.view_mode == "solution" and self.search_path:
            self.draw_solution_details(x, y)

    def draw_trace_details(self, step: SearchTraceStep, x: int, y: int) -> None:
        width = PANEL_W - 40
        card = pygame.Rect(x + 12, y + 183, PANEL_W - 24, 96)
        pygame.draw.rect(self.screen, COLORS["card_alt"], card, border_radius=10)
        title = f"01  CHỌN #{step.node_id}  ·  độ sâu {step.depth}"
        if step.is_goal:
            title += "  ·  ĐẠT ĐÍCH"
        self.draw_text(title, (x + 22, y + 192), COLORS["green"] if step.is_goal else COLORS["accent"], self.font_small)
        self.draw_heuristic(self.state, x + 22, y + 216)
        parent = f"  ·  từ cha #{step.parent_id}" if step.parent_id is not None else ""
        self.draw_text(self.describe_action(step.action) + parent, (x + 22, y + 239), COLORS["text"], self.font_small)
        self.draw_text("Đích: không lỗi nối, mọi ống nối về nguồn." if step.is_goal else "h nhỏ nhất; hòa điểm → độ sâu nhỏ hơn → vào hàng đợi trước.", (x + 22, y + 261), COLORS["muted"], self.font_tiny)

        new_count = sum(not candidate.duplicate for candidate in step.candidates)
        duplicates = len(step.candidates) - new_count
        self.draw_text(f"THỬ XOAY  ·  {new_count} mới  ·  {duplicates} trùng", (x + 20, y + 289), COLORS["text"], self.font_small)
        self.draw_text("PHÉP XOAY", (x + 28, y + 315), COLORS["faint"], self.font_tiny)
        self.draw_text("h(n) / Δh", (x + 281, y + 315), COLORS["faint"], self.font_tiny)
        self.draw_text("XỬ LÝ", (x + 389, y + 315), COLORS["faint"], self.font_tiny)
        candidates = sorted(step.candidates, key=lambda item: (item.duplicate, item.heuristic if item.heuristic is not None else 0, item.node_id))
        self.candidate_scroll = max(0, min(self.candidate_scroll, max(0, len(candidates) - 4)))
        self.candidate_rect = pygame.Rect(x + 20, y + 333, width, 108)
        next_id = step.frontier_preview[0].node_id if step.frontier_preview else None
        for row, candidate in enumerate(candidates[self.candidate_scroll:self.candidate_scroll + 4]):
            sy = y + 333 + row * 27
            rect = pygame.Rect(x + 20, sy, width, 25)
            pygame.draw.rect(self.screen, COLORS["card_alt"] if row % 2 == 0 else COLORS["card"], rect, border_radius=5)
            color = COLORS["faint"] if candidate.duplicate else COLORS["green"] if candidate.node_id == next_id else COLORS["text"]
            self.draw_text(self.describe_action(candidate.action), (x + 28, sy + 4), color, self.font_small)
            score = "—" if candidate.heuristic is None else f"{candidate.heuristic} ({candidate.heuristic - step.heuristic:+})"
            self.draw_text(score, (x + 281, sy + 5), color, self.font_tiny)
            label = "Trùng · bỏ qua" if candidate.duplicate else f"Thêm #{candidate.node_id}"
            self.draw_text(label, (x + 389, sy + 5), color, self.font_tiny)
        if not candidates:
            self.draw_text("Đã đạt đích; không sinh thêm nhánh.", (x + 28, y + 349), COLORS["green"], self.font_small)
        elif len(candidates) > 4:
            self.draw_text(f"Cuộn trong bảng để xem đủ {len(candidates)} phép xoay · xếp theo h(n)", (x + 20, y + 443), COLORS["faint"], self.font_tiny)

        self.draw_text(f"HÀNG ĐỢI  ·  {step.frontier_before:,} → {step.frontier_after:,} trạng thái", (x + 20, y + 466), COLORS["text"], self.font_small)
        for index, entry in enumerate(step.frontier_preview):
            rect = pygame.Rect(x + 20 + index * 103, y + 490, 98, 36)
            pygame.draw.rect(self.screen, COLORS["accent_dark"] if index == 0 else COLORS["card_alt"], rect, border_radius=7)
            color = COLORS["green"] if index == 0 else COLORS["muted"]
            self.draw_text(f"#{entry.node_id}", (rect.x + 6, rect.y + 2), color, self.font_tiny)
            self.draw_text(f"h={entry.heuristic} · sâu {entry.depth}", (rect.x + 6, rect.y + 18), color, self.font_tiny)
        next_text = "Đã gặp trạng thái đích; dừng tìm kiếm." if step.is_goal else "Xét tiếp: " + (f"#{next_id} (ô đầu) · ưu tiên theo h, độ sâu, thứ tự thêm." if next_id is not None else "Hàng đợi rỗng.")
        self.draw_text(next_text, (x + 20, y + 529), COLORS["muted"], self.font_tiny)
        self.draw_text(f"Tại bước này: đã tạo {step.generated:,}  ·  frontier lớn nhất {step.max_frontier:,}", (x + 20, y + 549), COLORS["muted"], self.font_tiny)
        result = self.search_result
        if self.search_computing:
            live = self.live_stats
            summary = f"Đang chạy: mở rộng {live['expanded']:,}  ·  đã tạo {live['generated']:,}  ·  {time.perf_counter() - self.search_started_at:.2f}s"
        elif result:
            summary = f"Tổng: mở rộng {result.nodes_expanded:,}  ·  tạo {result.nodes_generated:,}  ·  {result.time_sec:.3f}s"
        else:
            summary = ""
        self.draw_text(summary, (x + 20, y + 568), COLORS["faint"], self.font_tiny)
        expanded = result.nodes_expanded if result else self.live_stats["expanded"]
        if expanded > MAX_TRACE_STEPS:
            self.draw_text(f"Lưu {MAX_TRACE_STEPS:,} lượt đầu + đích (nếu có); lời giải giữ đủ các bước.", (x + 20, y + 587), COLORS["yellow"], self.font_tiny)

    def draw_heuristic(self, state: tuple[int, ...], x: int, y: int) -> None:
        mismatches = self.puzzle.count_mismatches(state)
        connected, active = self.puzzle._connectivity_stats(state)
        self.draw_text(f"h(n) = {mismatches} điểm lỗi nối + {active - connected} ô chưa nối nguồn = {mismatches + active - connected}", (x, y), COLORS["yellow"], self.font_small)

    def draw_solution_details(self, x: int, y: int) -> None:
        self.draw_text("ĐƯỜNG ĐI TỪ BAN ĐẦU ĐẾN ĐÍCH", (x + 20, y + 192), COLORS["accent"], self.font_bold)
        self.draw_heuristic(self.state, x + 20, y + 226)
        self.draw_text("Mỗi bước dưới đây là một phép xoay trên đường đi đã tìm được.", (x + 20, y + 257), COLORS["muted"], self.font_tiny)
        first = max(0, min(self.search_step - 3, len(self.search_path) - 7))
        self.solution_buttons = {}
        for index in range(first, min(first + 7, len(self.search_path))):
            sy = y + 291 + (index - first) * 34
            rect = pygame.Rect(x + 20, sy, PANEL_W - 40, 30)
            self.solution_buttons[index] = rect
            pygame.draw.rect(self.screen, COLORS["accent_dark"] if index == self.search_step else COLORS["card_alt"], rect, border_radius=7)
            action = self.describe_action(self.search_result.actions[index - 1]) if index and self.search_result else "Trạng thái ban đầu"
            self.draw_text(f"{index:02}   {action}", (x + 30, sy + 6), COLORS["text"], self.font_small)
            self.draw_text(f"h={self.puzzle.heuristic(self.search_path[index])}", (x + PANEL_W - 73, sy + 7), COLORS["green"], self.font_tiny)
        message = "Đã nối toàn bộ mạng ống về nguồn." if self.solved else "Dùng Lùi / Tiến để xem phép xoay trước và sau."
        self.draw_text(message, (x + 20, y + 546), COLORS["green"] if self.solved else COLORS["muted"], self.font_small)
        self.draw_text("Tab Quá trình tìm kiếm cho biết AI đã xét những nhánh nào.", (x + 20, y + 576), COLORS["faint"], self.font_tiny)

    def draw_footer(self) -> None:
        y = self.screen.get_height() - 27
        pygame.draw.line(self.screen, COLORS["border"], (BOARD_MARGIN, y - 10), (self.screen.get_width() - BOARD_MARGIN, y - 10))
        footer = f"G  Chạy AI    ← / →  Từng bước    Space  Phát/dừng    Tab  Đổi chế độ xem    R  Reset    1–4  Cỡ lưới    N  Bài mới    M  Mật độ    T  Màu    Seed {self.seed_value}"
        self.draw_text(footer, (BOARD_MARGIN, y), COLORS["faint"], self.font_tiny)

    def handle_click(self, position: tuple[int, int]) -> None:
        for mode, rect in self.inspector_buttons.items():
            if rect.collidepoint(position):
                self.set_view(mode)
                return
        if self.timeline_rect.inflate(0, 12).collidepoint(position):
            self.timeline_dragging = True
            self.seek_timeline(position[0])
            return
        if self.view_mode == "solution":
            for index, rect in getattr(self, "solution_buttons", {}).items():
                if rect.collidepoint(position):
                    self.select_step(index)
                    return
        for key, rect in self.puzzle_buttons.items():
            if rect.collidepoint(position):
                self.switch_puzzle(key)
                return
        if self.header_buttons.get("new", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.new_puzzle()
        elif self.header_buttons.get("mode", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.toggle_mode()
        elif self.header_buttons.get("theme", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.toggle_theme()
        elif self.action_buttons.get("run", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.run_greedy()
        elif self.action_buttons.get("step", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.step_search()
        elif self.action_buttons.get("back", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.step_search(-1)
        elif self.action_buttons.get("speed", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.cycle_speed()
        elif self.action_buttons.get("pause", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.toggle_pause()
        elif self.action_buttons.get("reset", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.reset()
        elif self.action_buttons.get("cancel", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.cancel_search()
        else:
            self.on_board_click(position)

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.unicode in PUZZLE_FILES:
                        self.switch_puzzle(event.unicode)
                    elif event.key == pygame.K_n:
                        self.new_puzzle()
                    elif event.key == pygame.K_t:
                        self.toggle_theme()
                    elif event.key == pygame.K_m:
                        self.toggle_mode()
                    elif event.key == pygame.K_g:
                        self.run_greedy()
                    elif event.key == pygame.K_s:
                        self.step_search()
                    elif event.key == pygame.K_RIGHT:
                        self.step_search()
                    elif event.key == pygame.K_LEFT:
                        self.step_search(-1)
                    elif event.key == pygame.K_HOME:
                        self.select_step(0)
                    elif event.key == pygame.K_END:
                        self.select_step(self.playback_length - 1)
                    elif event.key == pygame.K_TAB:
                        self.set_view("solution" if self.view_mode == "trace" else "trace")
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_c:
                        self.cancel_search()
                    elif event.key == pygame.K_SPACE:
                        self.toggle_pause()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.timeline_dragging = False
                elif event.type == pygame.MOUSEMOTION and self.timeline_dragging:
                    self.seek_timeline(event.pos[0])
                elif event.type == pygame.MOUSEWHEEL and self.view_mode == "trace":
                    if self.candidate_rect.collidepoint(pygame.mouse.get_pos()):
                        self.candidate_scroll -= event.y * 2
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    App().run()
