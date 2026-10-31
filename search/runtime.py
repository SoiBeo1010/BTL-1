"""Bookkeeping shared by the search strategies; frontier order stays in each solver."""
from __future__ import annotations

from dataclasses import dataclass
import time
import tracemalloc
from typing import Iterable

from puzzle import PipesPuzzle
from .common import FrontierEntry, SearchCandidate, SearchResult, SearchTraceStep, State, TraceCallback


@dataclass(frozen=True, slots=True)
class SearchNode:
    """An accepted path to a state, with an immutable parent for trace playback."""
    state: State
    parent: SearchNode | None = None
    action: str = ""
    depth: int = 0
    node_id: int = 0


@dataclass
class SearchMeasurement:
    elapsed: float = 0.0
    peak_kib: float = 0.0

    def __enter__(self) -> SearchMeasurement:
        self._owns_tracing = not tracemalloc.is_tracing()
        if self._owns_tracing:
            tracemalloc.start()
        self._started_at = time.perf_counter()
        return self

    def __exit__(self, *exc_info) -> None:
        self.elapsed = time.perf_counter() - self._started_at
        try:
            _, peak = tracemalloc.get_traced_memory()
            self.peak_kib = peak / 1024
        finally:
            if self._owns_tracing:
                tracemalloc.stop()


def validate_limits(max_nodes: int, max_depth: int | None, trace_limit: int) -> None:
    for name, value in (("max_nodes", max_nodes), ("max_depth", max_depth), ("trace_limit", trace_limit)):
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ValueError(f"{name} must be a nonnegative integer")


def is_duplicate(previous: SearchNode | None, depth: int, max_depth: int | None) -> bool:
    # A shorter path has more remaining depth than an earlier path to the same state.
    return previous is not None and (max_depth is None or previous.depth <= depth)


def record_trace(
    puzzle: PipesPuzzle,
    callback: TraceCallback | None,
    node: SearchNode,
    *,
    expanded: int,
    generated: int,
    max_frontier: int,
    frontier_before: int,
    frontier_after: int,
    candidates: list[SearchCandidate],
    preview: Iterable[tuple[SearchNode, int]],
    is_goal: bool,
    heuristic: int | None = None,
) -> None:
    if callback is None:
        return
    parent = node.parent
    callback(SearchTraceStep(
        number=expanded, node_id=node.node_id,
        parent_id=parent.node_id if parent is not None else None,
        state=node.state, parent_state=parent.state if parent is not None else None,
        action=node.action,
        heuristic=puzzle.heuristic(node.state) if heuristic is None else heuristic,
        depth=node.depth, frontier_before=frontier_before, frontier_after=frontier_after,
        generated=generated, max_frontier=max_frontier, candidates=tuple(candidates),
        frontier_preview=tuple(FrontierEntry(queued.node_id, queued.action, h, queued.depth)
                               for queued, h in preview),
        is_goal=is_goal,
    ))


def solved_start(algorithm: str, puzzle: PipesPuzzle, start: State, callback: TraceCallback | None) -> SearchResult:
    record_trace(puzzle, callback, SearchNode(start), expanded=0, generated=1,
                 max_frontier=1, frontier_before=1, frontier_after=0,
                 candidates=[], preview=(), is_goal=True)
    return SearchResult(algorithm, True, [start], [], 0, 1, 1, 0.0, 0.0, 0)


def build_result(
    algorithm: str, goal: SearchNode | None, expanded: int, generated: int,
    max_frontier: int, measurement: SearchMeasurement, reason: str,
    max_depth_reached: int = 0,
) -> SearchResult:
    path, actions = [], []
    current = goal
    while current is not None:
        path.append(current.state)
        if current.parent is not None:
            actions.append(current.action)
        current = current.parent
    path.reverse()
    actions.reverse()
    return SearchResult(
        algorithm, goal is not None, path, actions, expanded, generated,
        max_frontier, measurement.elapsed, measurement.peak_kib,
        len(actions) if goal is not None else -1, reason, max_depth_reached,
    )
