"""
Pipes Puzzle Engine
===================
Mỗi ô có 1 loại ống (type) và 1 góc xoay (rotation 0..3).
Hướng: 0=North, 1=East, 2=South, 3=West

Loại ống (canonical rotation 0):
  EMPTY   : []
  END     : [N]
  STRAIGHT: [N, S]      (dọc)
  ELBOW   : [N, E]      (góc)
  TEE     : [N, E, S]   (chữ T)
  CROSS   : [N, E, S, W]
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import List, Tuple, Optional

DIRS = [(-1,0),(0,1),(1,0),(0,-1)]  # N,E,S,W
OPPOSITE = [2,3,0,1]

BASE_CONNECTIONS = {
    "EMPTY":    [],
    "END":      [0],
    "STRAIGHT": [0,2],
    "ELBOW":    [0,1],
    "TEE":      [0,1,2],
    "CROSS":    [0,1,2,3],
}

def rotated_connections(cell_type: str, rot: int) -> List[int]:
    base = BASE_CONNECTIONS[cell_type]
    return sorted((d + rot) % 4 for d in base)

@dataclass
class Cell:
    type: str
    rotation: int  # 0..3
    locked: bool = False

    def connections(self) -> List[int]:
        return rotated_connections(self.type, self.rotation)

    def connections_with_rot(self, rot: int) -> List[int]:
        return rotated_connections(self.type, rot)

class PipesPuzzle:
    def __init__(self, rows: int, cols: int, cells: List[Cell], root_index: Optional[int] = None):
        self.rows = rows
        self.cols = cols
        self.cells = cells  # len = rows*cols
        assert len(cells) == rows*cols
        if root_index is not None and not 0 <= root_index < len(cells):
            raise ValueError("root_index must point to a cell in the puzzle")
        self.root_index = root_index

    @property
    def row(self) -> int:
        return self.rows

    @property
    def column(self) -> int:
        return self.cols

    @property
    def collumn(self) -> int:
        return self.cols

    def idx(self, r, c): return r*self.cols + c
    def rc(self, idx): return divmod(idx, self.cols)

    def get_connections(self, state: Tuple[int,...], idx: int) -> List[int]:
        cell = self.cells[idx]
        return rotated_connections(cell.type, state[idx])

    def initial_state(self) -> Tuple[int,...]:
        return tuple(c.rotation for c in self.cells)

    def is_goal(self, state: Tuple[int,...]) -> bool:
        return self.count_mismatches(state) == 0 and self.connectivity_ok(state)

    def count_mismatches(self, state: Tuple[int,...]) -> int:
        """Số cạnh lỗi = heuristic chính. 0 = solved."""
        mismatches = 0
        for r in range(self.rows):
            for c in range(self.cols):
                idx = self.idx(r,c)
                conns = set(self.get_connections(state, idx))
                for d, (dr, dc) in enumerate(DIRS):
                    nr, nc = r+dr, c+dc
                    has_open = d in conns
                    if nr < 0 or nr >= self.rows or nc < 0 or nc >= self.cols:
                        # biên: mở ra ngoài = lỗi
                        if has_open:
                            mismatches += 1
                    else:
                        nidx = self.idx(nr, nc)
                        nconns = set(self.get_connections(state, nidx))
                        od = OPPOSITE[d]
                        neighbor_has = od in nconns
                        if has_open != neighbor_has:
                            mismatches += 1
        # mỗi lỗi đếm 2 lần (2 phía) nên chia 2 cho đúng, nhưng giữ nguyên để heuristic phân biệt rõ
        # ta chia 2 để giá trị gọn
        return mismatches // 2

    def connectivity_ok(self, state: Tuple[int,...]) -> bool:
        """Kiểm tra mọi ống có nối thành một mạng từ ô gốc hay không."""
        connected, active = self._connectivity_stats(state)
        return connected == active

    def connected_cells(self, state: Tuple[int,...]) -> set[int]:
        """Return cells reachable from the root through currently matching edges."""
        active = {i for i in range(len(state)) if self.get_connections(state, i)}
        start = self.root_index
        if start is not None and start not in active:
            return set()
        if start is None:
            start = min(active) if active else None
        if start is None:
            return set()

        visited = {start}
        stack = [start]
        while stack:
            current = stack.pop()
            row, col = self.rc(current)
            for direction in self.get_connections(state, current):
                dr, dc = DIRS[direction]
                nr, nc = row + dr, col + dc
                if not (0 <= nr < self.rows and 0 <= nc < self.cols):
                    continue
                neighbour = self.idx(nr, nc)
                if neighbour in visited:
                    continue
                if OPPOSITE[direction] in self.get_connections(state, neighbour):
                    visited.add(neighbour)
                    stack.append(neighbour)
        return visited

    def _connectivity_stats(self, state: Tuple[int,...]) -> tuple[int, int]:
        """Return (cells connected to the start, cells containing a pipe)."""
        active = sum(bool(self.get_connections(state, i)) for i in range(len(state)))
        return len(self.connected_cells(state)), active

    def successors(self, state: Tuple[int,...]):
        """Sinh trạng thái bằng cách chọn một hướng xoay của một ô."""
        for i, cell in enumerate(self.cells):
            if cell.locked:
                continue
            # CROSS xoay không đổi, EMPTY không đổi -> skip
            if cell.type in ("CROSS", "EMPTY"):
                continue
            # Puzzle mới có nguồn cố định nên cho phép chọn trực tiếp
            # 90/180/270 độ, tránh việc Greedy bị kẹt ở góc heuristic xấu.
            # Puzzle cũ không có root vẫn giữ successor 90 độ để tương thích.
            seen_rotations = set()
            steps_options = (1, 2, 3) if self.root_index is not None else (1,)
            for steps in steps_options:
                new_rot = (state[i] + steps) % 4
                if new_rot in seen_rotations:
                    continue
                seen_rotations.add(new_rot)
                lst = list(state)
                lst[i] = new_rot
                yield tuple(lst), f"R{i}+{steps}"

    def heuristic(self, state: Tuple[int,...]) -> int:
        """Greedy heuristic: số mismatches + phạt rời rạc."""
        h = self.count_mismatches(state)
        # Phạt theo số ô chưa nối được về gốc, giúp Greedy ưu tiên mở rộng
        # một mạng duy nhất thay vì chỉ sửa các cặp cạnh cục bộ.
        connected, active = self._connectivity_stats(state)
        h += max(0, active - connected)
        return h

    # --- I/O ---
    @classmethod
    def from_dict(cls, data: dict) -> "PipesPuzzle":
        rows, cols = data["rows"], data["cols"]
        cells = []
        for c in data["cells"]:
            cells.append(Cell(type=c["type"], rotation=c["rotation"], locked=c.get("locked", False)))
        return cls(rows, cols, cells, root_index=data.get("root"))

    @classmethod
    def from_json(cls, path: str) -> "PipesPuzzle":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def to_dict(self):
        return {
            "rows": self.rows, "cols": self.cols,
            "root": self.root_index,
            "cells": [
                {"type": c.type, "rotation": s, "locked": c.locked}
                for c, s in zip(self.cells, self.initial_state())
            ],
        }

    def pretty(self, state: Tuple[int,...] = None) -> str:
        if state is None:
            state = self.initial_state()
        # ký tự unicode đơn giản
        glyph = {
            frozenset(): "·",
            frozenset([0]): "╵", frozenset([1]): "╶", frozenset([2]): "╷", frozenset([3]): "╴",
            frozenset([0,2]): "│", frozenset([1,3]): "─",
            frozenset([0,1]): "└", frozenset([1,2]): "┌", frozenset([2,3]): "┐", frozenset([0,3]): "┘",
            frozenset([0,1,2]): "├", frozenset([1,2,3]): "┬", frozenset([0,2,3]): "┤", frozenset([0,1,3]): "┴",
            frozenset([0,1,2,3]): "┼",
        }
        lines = []
        for r in range(self.rows):
            row = ""
            for c in range(self.cols):
                idx = self.idx(r,c)
                conns = frozenset(self.get_connections(state, idx))
                # STRAIGHT ngang là 1,3
                row += glyph.get(conns, "?") + " "
            lines.append(row)
        return "\n".join(lines)


def make_sample_puzzles():
    """Tạo 3 puzzle mẫu độ khó tăng dần để benchmark."""
    puzzles = {}

    # Easy 3x3 - 6 ô xoay được
    puzzles["easy_3x3"] = PipesPuzzle.from_dict({
        "rows": 3, "cols": 3,
        "cells": [
            {"type": "ELBOW", "rotation": 1}, {"type": "STRAIGHT", "rotation": 0}, {"type": "ELBOW", "rotation": 2},
            {"type": "END", "rotation": 3},   {"type": "CROSS", "rotation": 0, "locked": True}, {"type": "END", "rotation": 1},
            {"type": "ELBOW", "rotation": 0}, {"type": "STRAIGHT", "rotation": 0}, {"type": "ELBOW", "rotation": 3},
        ]
    })

    # Medium 4x4
    puzzles["medium_4x4"] = PipesPuzzle.from_dict({
        "rows": 4, "cols": 4,
        "cells": [
            {"type": "ELBOW", "rotation": 2}, {"type": "TEE", "rotation": 1}, {"type": "STRAIGHT", "rotation": 1}, {"type": "ELBOW", "rotation": 3},
            {"type": "TEE", "rotation": 0}, {"type": "CROSS", "rotation": 0, "locked": True}, {"type": "ELBOW", "rotation": 0}, {"type": "TEE", "rotation": 2},
            {"type": "STRAIGHT", "rotation": 0}, {"type": "ELBOW", "rotation": 3}, {"type": "TEE", "rotation": 3}, {"type": "END", "rotation": 1},
            {"type": "ELBOW", "rotation": 1}, {"type": "STRAIGHT", "rotation": 1}, {"type": "ELBOW", "rotation": 0}, {"type": "END", "rotation": 2},
        ]
    })

    # Hard 5x5
    puzzles["hard_5x5"] = PipesPuzzle.from_dict({
        "rows": 5, "cols": 5,
        "cells": [
            {"type": "ELBOW", "rotation": 1}, {"type": "TEE", "rotation": 2}, {"type": "STRAIGHT", "rotation": 0}, {"type": "ELBOW", "rotation": 2}, {"type": "END", "rotation": 0},
            {"type": "TEE", "rotation": 3}, {"type": "CROSS", "rotation": 0, "locked": True}, {"type": "ELBOW", "rotation": 1}, {"type": "TEE", "rotation": 0}, {"type": "STRAIGHT", "rotation": 1},
            {"type": "STRAIGHT", "rotation": 1}, {"type": "ELBOW", "rotation": 0}, {"type": "TEE", "rotation": 1}, {"type": "CROSS", "rotation": 0, "locked": True}, {"type": "ELBOW", "rotation": 3},
            {"type": "ELBOW", "rotation": 2}, {"type": "TEE", "rotation": 3}, {"type": "STRAIGHT", "rotation": 0}, {"type": "ELBOW", "rotation": 1}, {"type": "END", "rotation": 2},
            {"type": "END", "rotation": 1}, {"type": "STRAIGHT", "rotation": 1}, {"type": "ELBOW", "rotation": 3}, {"type": "END", "rotation": 0}, {"type": "ELBOW", "rotation": 0},
        ]
    })

    # Tiny 2x3 puzzle for a fast demo.
    puzzles["tiny_2x3"] = PipesPuzzle.from_dict({
        "rows": 2, "cols": 3,
        "cells": [
            {"type": "ELBOW", "rotation": 1}, {"type": "STRAIGHT", "rotation": 0}, {"type": "ELBOW", "rotation": 2},
            {"type": "ELBOW", "rotation": 0}, {"type": "STRAIGHT", "rotation": 0}, {"type": "ELBOW", "rotation": 3},
        ]
    })

    return puzzles
