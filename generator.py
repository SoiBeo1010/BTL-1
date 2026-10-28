"""Procedural, always-solvable Pipes puzzle generator."""
from __future__ import annotations

import json
import os
import random
from typing import Iterable

from puzzle import Cell, PipesPuzzle, rotated_connections


DIRECTIONS = [(-1, 0), (0, 1), (1, 0), (0, -1)]
OPPOSITE = [2, 3, 0, 1]


def _neighbours(rows: int, cols: int, index: int) -> Iterable[tuple[int, int]]:
    row, col = divmod(index, cols)
    for direction, (dr, dc) in enumerate(DIRECTIONS):
        nr, nc = row + dr, col + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            yield row * cols + col, nr * cols + nc


def _direction(rows: int, cols: int, source: int, target: int) -> int:
    sr, sc = divmod(source, cols)
    tr, tc = divmod(target, cols)
    dr, dc = tr - sr, tc - sc
    return DIRECTIONS.index((dr, dc))


def _random_network(
    rows: int,
    cols: int,
    rng: random.Random,
    start: int | None = None,
    add_loops: bool = True,
) -> list[set[int]]:
    """Build a connected random network without boundary leaks."""
    total = rows * cols
    connections = [set() for _ in range(total)]
    visited = {rng.randrange(total) if start is None else start}
    stack = list(visited)

    # Randomized depth-first spanning tree: every cell belongs to the network.
    while stack:
        current = stack[-1]
        candidates = [
            target
            for _, target in _neighbours(rows, cols, current)
            if target not in visited
        ]
        if not candidates:
            stack.pop()
            continue
        target = rng.choice(candidates)
        direction = _direction(rows, cols, current, target)
        connections[current].add(direction)
        connections[target].add(OPPOSITE[direction])
        visited.add(target)
        stack.append(target)

    if not add_loops:
        return connections

    # Add a few safe extra edges to create loops and T/CROSS junctions.
    possible = []
    for source in range(total):
        for _, target in _neighbours(rows, cols, source):
            if source >= target:
                continue
            direction = _direction(rows, cols, source, target)
            if direction not in connections[source]:
                possible.append((source, target, direction))
    rng.shuffle(possible)
    loop_chance = min(0.30, 0.08 + rows * cols / 450)
    for source, target, direction in possible:
        if len(connections[source]) >= 4 or len(connections[target]) >= 4:
            continue
        if rng.random() < loop_chance:
            connections[source].add(direction)
            connections[target].add(OPPOSITE[direction])

    return connections


def _piece_for_connections(connections: set[int]) -> tuple[str, int]:
    """Return the piece type and rotation that exactly matches connections."""
    size = len(connections)
    if size == 1:
        piece_type = "END"
    elif size == 2:
        opposite = {0, 2}, {1, 3}
        piece_type = "STRAIGHT" if connections in opposite else "ELBOW"
    elif size == 3:
        piece_type = "TEE"
    elif size == 4:
        return "CROSS", 0
    else:
        raise ValueError("A generated network cell must have at least one connection")

    for rotation in range(4):
        if set(rotated_connections(piece_type, rotation)) == connections:
            return piece_type, rotation
    raise ValueError(f"Cannot encode connections: {connections}")


def _scramble_sparse(
    rows: int,
    cols: int,
    cells: list[Cell],
    rng: random.Random,
) -> list[int]:
    """Break matching edges across the board without removing any pipes."""
    rotations = [cell.rotation for cell in cells]
    connections = [set(cell.connections()) for cell in cells]
    untouched = [
        index
        for index, cell in enumerate(cells)
        if not cell.locked and cell.type not in ("CROSS", "EMPTY")
    ]
    # Prefer rotations that break several existing edges at once. This spreads
    # gaps across the board while keeping the distance to a solution bounded.
    scramble_moves = min(max(4, rows * cols // 3), len(untouched))
    for _ in range(scramble_moves):
        best_breaks = 0
        candidates: list[tuple[int, int, set[int]]] = []
        for index in untouched:
            row, col = divmod(index, cols)
            incoming = {
                direction
                for direction, (dr, dc) in enumerate(DIRECTIONS)
                if 0 <= row + dr < rows
                and 0 <= col + dc < cols
                and OPPOSITE[direction] in connections[(row + dr) * cols + col + dc]
            }
            original = connections[index]
            seen = {frozenset(original)}
            for steps in (1, 2, 3):
                rotation = (rotations[index] + steps) % 4
                rotated = frozenset(rotated_connections(cells[index].type, rotation))
                if rotated in seen:
                    continue
                seen.add(rotated)
                breaks = len(original & incoming) - len(rotated & incoming)
                if breaks > best_breaks:
                    best_breaks = breaks
                    candidates = []
                if breaks == best_breaks and breaks > 0:
                    candidates.append((index, rotation, set(rotated)))
        if not candidates:
            break
        index, rotation, rotated = rng.choice(candidates)
        rotations[index] = rotation
        connections[index] = rotated
        untouched.remove(index)
    return rotations


def make_random_puzzle(
    rows: int,
    cols: int,
    seed: int | None = None,
    sparse: bool = False,
) -> tuple[PipesPuzzle, tuple[int, ...]]:
    """Create a random puzzle and its hidden solved state.

    Both modes use every cell in one connected network. Dense mode adds loops,
    while Sparse keeps only the spanning tree and selects rotations that break
    matching edges across the initial board. The center cell is the fixed
    source; every other non-cross piece remains rotatable.
    """
    if rows < 3 or cols < 3:
        raise ValueError("Random puzzles need at least a 3x3 grid")
    rng = random.Random(seed)
    root_index = (rows // 2) * cols + (cols // 2)
    network = _random_network(rows, cols, rng, start=root_index, add_loops=not sparse)
    solved_cells: list[Cell] = []
    for index, connections in enumerate(network):
        piece_type, rotation = _piece_for_connections(connections)
        locked = index == root_index
        solved_cells.append(Cell(piece_type, rotation, locked=locked))

    scrambled_rotations = [cell.rotation for cell in solved_cells]
    movable = [
        index
        for index, cell in enumerate(solved_cells)
        if not cell.locked and cell.type != "CROSS"
    ]
    if sparse:
        scrambled_rotations = _scramble_sparse(rows, cols, solved_cells, rng)
    else:
        # Dense boards use a short scramble to keep the Greedy demo responsive.
        scramble_moves = {3: 3, 4: 4, 5: 3, 6: 3}.get(max(rows, cols), rows * cols // 6)
        previous = None
        touched: set[int] = set()
        for _ in range(min(scramble_moves, len(movable))):
            fresh = [index for index in movable if index not in touched]
            candidates = fresh or ([index for index in movable if index != previous] or movable)
            index = rng.choice(candidates)
            cell = solved_cells[index]
            if cell.type == "STRAIGHT":
                scrambled_rotations[index] = 1 - scrambled_rotations[index]
            else:
                scrambled_rotations[index] = (scrambled_rotations[index] + 1) % 4
            touched.add(index)
            previous = index

    # Avoid returning the solved state when a short random walk cancels itself.
    if scrambled_rotations == [cell.rotation for cell in solved_cells]:
        index = rng.choice(movable)
        cell = solved_cells[index]
        scrambled_rotations[index] = (cell.rotation + 1) % (2 if cell.type == "STRAIGHT" else 4)

    scrambled_cells = [
        Cell(cell.type, rotation, locked=cell.locked)
        for cell, rotation in zip(solved_cells, scrambled_rotations)
    ]
    puzzle = PipesPuzzle(rows, cols, scrambled_cells, root_index=root_index)
    solved_state = tuple(cell.rotation for cell in solved_cells)
    return puzzle, solved_state


def make_loop_puzzle(rows: int, cols: int, seed: int | None = None):
    """Backward-compatible wrapper for the original perimeter generator."""
    rng = random.Random(seed)
    cells_solved: list[Cell] = []
    for row in range(rows):
        for col in range(cols):
            is_border = row == 0 or row == rows - 1 or col == 0 or col == cols - 1
            is_corner = (row in (0, rows - 1)) and (col in (0, cols - 1))
            if is_corner:
                if row == 0 and col == 0:
                    rotation = 1
                elif row == 0 and col == cols - 1:
                    rotation = 2
                elif row == rows - 1 and col == cols - 1:
                    rotation = 3
                else:
                    rotation = 0
                cells_solved.append(Cell("ELBOW", rotation))
            elif is_border:
                cells_solved.append(Cell("STRAIGHT", 1 if row in (0, rows - 1) else 0))
            else:
                cells_solved.append(Cell("EMPTY", 0, locked=True))

    cells_scrambled = []
    for cell in cells_solved:
        if cell.type == "EMPTY":
            cells_scrambled.append(Cell(cell.type, 0, locked=True))
        elif cell.type == "STRAIGHT":
            cells_scrambled.append(Cell(cell.type, rng.randrange(2)))
        else:
            cells_scrambled.append(Cell(cell.type, rng.randrange(4)))
    puzzle = PipesPuzzle(rows, cols, cells_scrambled)
    return puzzle, tuple(cell.rotation for cell in cells_solved)


def save_puzzle(puzzle: PipesPuzzle, path: str) -> None:
    data = {
        "rows": puzzle.rows,
        "cols": puzzle.cols,
        "root": puzzle.root_index,
        "cells": [
            {"type": cell.type, "rotation": rotation, "locked": cell.locked}
            for cell, rotation in zip(puzzle.cells, puzzle.initial_state())
        ],
    }
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    os.makedirs("puzzles", exist_ok=True)
    configs = [("tiny_3x3", 3, 3, 42), ("easy_4x4", 4, 4, 1), ("medium_5x5", 5, 5, 7), ("hard_6x6", 6, 6, 99)]
    for name, rows, cols, seed in configs:
        puzzle, solved = make_random_puzzle(rows, cols, seed=seed)
        print(f"{name}: h0={puzzle.heuristic(puzzle.initial_state())} solved={puzzle.is_goal(solved)}")
        save_puzzle(puzzle, f"puzzles/{name}.json")
    # Match the perimeter-only sample inputs used for size comparisons.
    puzzle, solved = make_loop_puzzle(7, 7, seed=42)
    print(f"large_7x7: h0={puzzle.heuristic(puzzle.initial_state())} solved={puzzle.is_goal(solved)}")
    save_puzzle(puzzle, "puzzles/large_7x7.json")
    print("Saved to puzzles/")
