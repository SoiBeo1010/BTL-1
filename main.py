"""Pipes Puzzle dashboard powered by Greedy Best-First Search."""
from __future__ import annotations

import json
import os
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
from search import SearchResult, greedy_best_first

BOARD_W = 760
HEADER_H = 164
BOARD_MARGIN = 24
CARD_H = 605
PANEL_W = 328
GAP = 26
FPS = 60
MAX_NODES = 500_000
GRID_AREA_TOP = 82
GRID_AREA_BOTTOM = 72
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
        self.live_stats = {"expanded": 0, "generated": 1, "frontier": 1, "max_frontier": 1}
        self.displayed_max_frontier = 0
        self.frontier_animation_start = 0
        self.solved = self.puzzle.is_goal(self.state)
        self.status = "SOLVED" if self.solved else "READY"
        self.status_detail = "T\u1ef1 xoay c\u00e1c \u00f4 ho\u1eb7c nh\u1ea5n G \u0111\u1ec3 Greedy t\u00ecm l\u1eddi gi\u1ea3i."
        self.auto_delay = 0.13
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
        self.displayed_max_frontier = 0
        self.search_cancel_requested = True
        self.search_computing = False
        self.search_pending_result = None
        self.search_running = False
        self.search_paused = False

    def reset(self) -> None:
        """Reset the current generated layout without changing its seed."""
        self._invalidate_search()
        self.state = self.puzzle.initial_state()
        self.previous_state = None
        self.search_result = None
        self.search_path = []
        self.search_step = 0
        self.search_running = False
        self.search_paused = False
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
        self.search_result = None
        self.search_path = []
        self.search_step = 0
        self.search_running = False
        self.search_paused = False
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
        self.displayed_max_frontier = 0
        self.search_path = []
        self.search_step = 0
        self.search_running = False
        self.search_paused = False

    def cancel_search(self) -> None:
        if self.search_computing:
            self.search_cancel_requested = True
            self.search_running = False
            self.search_path = []
            self.search_step = 0
            self.status = "CANCELLED"
            self.status_detail = "\u0110\u00e3 h\u1ee7y search hi\u1ec7n t\u1ea1i."
            return
        if self.search_running or self.search_path:
            self.search_running = False
            self.search_paused = False
            self.search_path = []
            self.search_step = 0
            self.status = "CANCELLED"
            self.status_detail = "\u0110\u00e3 h\u1ee7y ho\u1ea1t \u1ea3nh l\u1eddi gi\u1ea3i hi\u1ec7n t\u1ea1i."

    def on_board_click(self, position: tuple[int, int]) -> None:
        if self.search_running or self.search_computing:
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
        )
        if token == self.search_token:
            self.search_pending_result = result

    def _finish_search(self, result: SearchResult) -> None:
        self.search_result = result
        self.frontier_animation_start = self.displayed_max_frontier
        self.search_path = result.path
        self.search_step = 0
        self.last_step_time = time.perf_counter()
        self.search_cancel_requested = False
        if result.found and result.path:
            self.search_running = len(result.path) > 1
            self.solved = len(result.path) == 1
            self.status = "SOLVED" if self.solved else "SOLUTION READY"
            self.status_detail = f"\u0110\u00e3 t\u00ecm th\u1ea5y l\u1eddi gi\u1ea3i v\u1edbi {result.depth} l\u1ea7n xoay."
        else:
            self.search_running = False
            self.status = "NO SOLUTION"
            self.status_detail = f"D\u1eebng sau {result.nodes_generated:,} tr\u1ea1ng th\u00e1i \u0111\u01b0\u1ee3c t\u1ea1o."
        if not self.search_running:
            self.displayed_max_frontier = result.max_frontier

    def run_greedy(self) -> None:
        if self.search_running or self.search_computing:
            return
        if self.search_worker is not None and self.search_worker.is_alive():
            return
        self.status = "SEARCHING"
        self.status_detail = "Greedy dang mo rong trang thai co h(n) thap nhat..."
        self.solved = False
        self.search_result = None
        self.search_path = []
        self.search_step = 0
        self.search_paused = False
        self.search_cancel_requested = False
        self.search_pending_result = None
        self.search_token += 1
        token = self.search_token
        self.search_computing = True
        self.search_started_at = time.perf_counter()
        self.live_stats = {"expanded": 0, "generated": 1, "frontier": 1, "max_frontier": 1}
        self.displayed_max_frontier = 0
        self.draw()
        pygame.display.flip()
        pygame.event.pump()

        working_puzzle = PipesPuzzle(
            self.puzzle.rows,
            self.puzzle.cols,
            self.puzzle.cells,
            root_index=self.puzzle.root_index,
        )
        self.search_worker = threading.Thread(
            target=self._search_worker,
            args=(token, working_puzzle, self.state),
            name="greedy-search",
            daemon=True,
        )
        self.search_worker.start()

    def step_search(self) -> None:
        if not self.search_path:
            self.run_greedy()
            return
        if self.search_step >= len(self.search_path) - 1:
            self.search_running = False
            self.solved = self.puzzle.is_goal(self.state)
            return
        self.previous_state = self.state
        self.search_step += 1
        self.state = self.search_path[self.search_step]
        self.last_step_time = time.perf_counter()
        if self.search_step >= len(self.search_path) - 1:
            self.search_running = False
            self.solved = self.puzzle.is_goal(self.state)
            self.status = "SOLVED" if self.solved else "READY"
            self.status_detail = "\u0110\u00e3 \u00e1p d\u1ee5ng l\u1eddi gi\u1ea3i. Nh\u1ea5n R ho\u1eb7c N \u0111\u1ec3 ch\u01a1i l\u1ea1i."
        else:
            self.status = "ANIMATING"
            self.status_detail = f"\u0110ang \u00e1p d\u1ee5ng l\u1ea7n xoay {self.search_step}/{len(self.search_path) - 1}."

    def toggle_pause(self) -> None:
        if not self.search_path or self.solved:
            return
        self.search_paused = not self.search_paused
        self.status = "PAUSED" if self.search_paused else "ANIMATING"
        self.status_detail = "Nh\u1ea5n SPACE \u0111\u1ec3 ti\u1ebfp t\u1ee5c." if self.search_paused else "\u0110ang \u00e1p d\u1ee5ng \u0111\u01b0\u1eddng \u0111i c\u1ee7a Greedy."
        self.last_step_time = time.perf_counter()

    def update(self) -> None:
        if self.search_computing:
            # Reserve the last unit for the final solution step.
            frontier_target = max(0, self.live_stats["max_frontier"] - 1)
            if not self.search_cancel_requested:
                self.displayed_max_frontier = min(frontier_target, self.displayed_max_frontier + 1)
            if self.search_pending_result is not None:
                result = self.search_pending_result
                self.search_pending_result = None
                self.search_computing = False
                self.search_worker = None
                if not self.search_cancel_requested:
                    self._finish_search(result)
                else:
                    self.displayed_max_frontier = 0
            elif self.search_worker is not None and not self.search_worker.is_alive():
                self.search_computing = False
                self.search_worker = None
            return

        if self.search_running and not self.search_paused and self.search_path:
            if time.perf_counter() - self.last_step_time >= self.auto_delay:
                self.step_search()

        if self.search_result is None:
            self.displayed_max_frontier = 0
        elif not self.search_running:
            self.displayed_max_frontier = self.search_result.max_frontier
        else:
            # Interpolate across solution steps so both animations end together.
            progress = float(self.search_step)
            if not self.search_paused:
                progress += min(1.0, (time.perf_counter() - self.last_step_time) / self.auto_delay)
            progress /= len(self.search_path) - 1
            remaining = self.search_result.max_frontier - self.frontier_animation_start
            frontier_target = self.frontier_animation_start + int(remaining * progress)
            self.displayed_max_frontier = min(
                self.search_result.max_frontier - 1,
                max(self.displayed_max_frontier, frontier_target),
            )

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
        self.draw_text("Nối các đầu ống. Khám phá một mạng lưới mới mỗi lần chơi.", (BOARD_MARGIN + 2, 66), COLORS["muted"], self.font_small)

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
        self.draw_text("Xanh: n\u1ed1i kh\u1edbp   |   \u0110\u1ecf: l\u1ed7i k\u1ebft n\u1ed1i   |   Click \u00f4 \u0111\u1ec3 xoay", (BOARD_MARGIN + 14, self.board_top + 49), COLORS["muted"], self.font_tiny)
        pill = pygame.Rect(BOARD_MARGIN + BOARD_W - 130, self.board_top + 18, 116, 27)
        pygame.draw.rect(self.screen, COLORS["card_alt"], pill, border_radius=12)
        self.draw_text(f"h={self.puzzle.heuristic(self.state)}  ·  {self.puzzle.count_mismatches(self.state)} lỗi", (pill.x + 10, pill.y + 7), COLORS["accent"], self.font_tiny)

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
        ]
        for index, (label, color) in enumerate(legend_items):
            x = BOARD_MARGIN + 48 + index * 174
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
        x = self.panel_x
        y = self.board_top
        width = PANEL_W
        panel = pygame.Rect(x, self.board_top, width, CARD_H)
        self.draw_panel(panel)

        if self.status == "SOLVED":
            heading, heading_color = "Đã giải xong", COLORS["green"]
        elif self.status in ("SEARCHING", "ANIMATING"):
            heading, heading_color = "Đang khám phá", COLORS["accent"]
        elif self.status == "PAUSED":
            heading, heading_color = "Đang tạm dừng", COLORS["yellow"]
        elif self.status == "NO SOLUTION":
            heading, heading_color = "Chưa tìm thấy lời giải", COLORS["red"]
        else:
            heading, heading_color = "Sẵn sàng khám phá", COLORS["accent"]
        self.draw_text(heading, (x + 20, y + 25), heading_color, self.font_title)
        self.draw_wrapped_text(
            self.status_detail,
            (x + 20, y + 64),
            width - 40,
            COLORS["muted"],
            self.font_tiny,
        )

        result = self.search_result
        if self.search_computing:
            live = self.live_stats
            metrics = [
                ("\u0110\u00c3 M\u1ede R\u1ed8NG", f"{live['expanded']:,}"),
                ("\u0110\u00c3 T\u1ea0O", f"{live['generated']:,}"),
                ("FRONTIER MAX", f"{self.displayed_max_frontier:,}"),
                ("TH\u1edcI GIAN", f"{max(0.0, time.perf_counter() - self.search_started_at):.2f}s"),
            ]
        else:
            metrics = [
                ("\u0110\u00c3 M\u1ede R\u1ed8NG", f"{result.nodes_expanded:,}" if result else "0"),
                ("\u0110\u00c3 T\u1ea0O", f"{result.nodes_generated:,}" if result else "0"),
                ("FRONTIER MAX", f"{self.displayed_max_frontier:,}"),
                ("TH\u1edcI GIAN", f"{result.time_sec:.2f}s" if result else "0.00s"),
            ]
        stats = pygame.Rect(x + 20, y + 105, width - 40, 145)
        self.draw_panel(stats)
        for i, (label, value) in enumerate(metrics):
            col, row = i % 2, i // 2
            sx = stats.x + 14 + col * 153
            sy = stats.y + 16 + row * 62
            self.draw_text(label, (sx, sy), COLORS["faint"], self.font_tiny)
            self.draw_text(value, (sx, sy + 17), COLORS["text"], self.font_number)

        self.action_buttons = {}
        run_rect = pygame.Rect(x + 20, y + 268, width - 40, 44)
        self.action_buttons["run"] = run_rect
        self.draw_button(run_rect, "Giải bằng Greedy", "G", primary=True, disabled=self.search_running or self.search_computing)
        half = (width - 52) // 2
        step_rect = pygame.Rect(x + 20, y + 324, half, 40)
        pause_rect = pygame.Rect(x + 32 + half, y + 324, half, 40)
        self.action_buttons["step"] = step_rect
        self.action_buttons["pause"] = pause_rect
        self.draw_button(step_rect, "Một bước", "S")
        can_pause = bool(self.search_path) and not self.solved
        self.draw_button(
            pause_rect,
            "D\u1eebng" if not self.search_paused else "Ti\u1ebfp t\u1ee5c",
            "Space",
            disabled=not can_pause,
        )
        reset_rect = pygame.Rect(x + 20, y + 380, half, 40)
        cancel_rect = pygame.Rect(x + 32 + half, y + 380, half, 40)
        self.action_buttons["reset"] = reset_rect
        self.action_buttons["cancel"] = cancel_rect
        self.draw_button(reset_rect, "Reset", "R")
        self.draw_button(cancel_rect, "Hủy", "C", disabled=not (self.search_computing or self.search_running or self.search_path))

        pygame.draw.line(self.screen, COLORS["border"], (x + 20, y + 455), (x + width - 20, y + 455))
        self.draw_text(f"SEED  {self.seed_value}", (x + 20, y + 480), COLORS["accent"], self.font_tiny)
        self.draw_text("Click ô để xoay ống  ·  h(n) càng nhỏ càng gần đích", (x + 20, y + 509), COLORS["muted"], self.font_tiny)
        self.draw_text(f"Bước: {self.search_step}/{result.depth if result and result.found else 0}", (x + 20, y + 538), COLORS["muted"], self.font_tiny)

    def draw_footer(self) -> None:
        y = self.screen.get_height() - 27
        pygame.draw.line(self.screen, COLORS["border"], (BOARD_MARGIN, y - 10), (self.screen.get_width() - BOARD_MARGIN, y - 10))
        footer = "1–4  Đổi cỡ lưới     N  Bài toán mới     M  Mật độ     T  Bảng màu     Click  Xoay ống     Esc  Thoát"
        self.draw_text(footer, (BOARD_MARGIN, y), COLORS["faint"], self.font_tiny)

    def handle_click(self, position: tuple[int, int]) -> None:
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
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_c:
                        self.cancel_search()
                    elif event.key == pygame.K_SPACE:
                        self.toggle_pause()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    App().run()
