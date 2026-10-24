"""Greedy Best-First Search for the Pipes puzzle."""
from __future__ import annotations

import heapq
import time
import tracemalloc
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from puzzle import PipesPuzzle

State = Tuple[int, ...]
ParentMap = Dict[State, Tuple[Optional[State], str]]
ProgressCallback = Callable[[State, int, int, int], None]
CancelCheck = Callable[[], bool]


@dataclass
class SearchResult:
    algorithm: str
    found: bool
    path: List[State]
    actions: List[str]
    nodes_expanded: int
    nodes_generated: int
    max_frontier: int
    time_sec: float
    peak_memory_kb: float
    depth: int = 0


def reconstruct_path(parents: ParentMap, goal: State, start: Optional[State] = None) -> tuple[List[State], List[str]]:
    path: List[State] = []
    actions: List[str] = []
    current: Optional[State] = goal
    while current is not None:
        path.append(current)
        parent, action = parents[current]
        if parent is not None:
            actions.append(action)
        current = parent
    path.reverse()
    actions.reverse()
    return path, actions


def greedy_best_first(
    puzzle: PipesPuzzle,
    max_nodes: int = 500_000,
    callback: Optional[Callable[[State, int, int], None]] = None,
    start_state: Optional[State] = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_check: Optional[CancelCheck] = None,
) -> SearchResult:
    """Solve ``puzzle`` by always expanding the state with the lowest h(n)."""
    start = start_state if start_state is not None else puzzle.initial_state()
    if puzzle.is_goal(start):
        return SearchResult(
            "Greedy Best-First", True, [start], [], 0, 1, 1, 0.0, 0.0, 0
        )

    tracemalloc.start()
    started_at = time.perf_counter()
    parents: ParentMap = {start: (None, "")}
    depths: Dict[State, int] = {start: 0}
    visited = {start}
    frontier: list[tuple[int, int, int, State]] = []
    heapq.heappush(frontier, (puzzle.heuristic(start), 0, 0, start))

    tie_breaker = 1
    expanded = 0
    generated = 1
    max_frontier = 1
    goal: Optional[State] = None

    while frontier and generated <= max_nodes and not (cancel_check and cancel_check()):
        _, _, _, state = heapq.heappop(frontier)
        expanded += 1
        if callback is not None:
            callback(state, expanded, len(frontier))
        if progress_callback is not None:
            progress_callback(state, expanded, generated, len(frontier))
        if puzzle.is_goal(state):
            goal = state
            break

        for successor, action in puzzle.successors(state):
            if cancel_check is not None and cancel_check():
                break
            if successor in visited:
                continue
            visited.add(successor)
            parents[successor] = (state, action)
            depths[successor] = depths[state] + 1
            generated += 1
            heapq.heappush(
                frontier,
                (puzzle.heuristic(successor), depths[successor], tie_breaker, successor),
            )
            tie_breaker += 1
            if generated > max_nodes:
                break
        max_frontier = max(max_frontier, len(frontier))
        if progress_callback is not None:
            progress_callback(state, expanded, generated, len(frontier))

    elapsed = time.perf_counter() - started_at
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    if goal is None:
        return SearchResult(
            "Greedy Best-First", False, [], [], expanded, generated,
            max_frontier, elapsed, peak / 1024, -1,
        )

    path, actions = reconstruct_path(parents, goal)
    return SearchResult(
        "Greedy Best-First", True, path, actions, expanded, generated,
        max_frontier, elapsed, peak / 1024, len(path) - 1,
    )
