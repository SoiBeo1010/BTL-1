"""Greedy Best-First Search for the Pipes puzzle."""
from __future__ import annotations

import heapq
import time
import tracemalloc
from typing import Callable, Dict, Optional

from puzzle import PipesPuzzle
from .common import (
    CancelCheck, FrontierEntry, ParentMap, ProgressCallback, SearchCandidate,
    SearchResult, SearchTraceStep, State, TraceCallback, reconstruct_path,
)


def greedy_best_first(
    puzzle: PipesPuzzle,
    max_nodes: int = 500_000,
    callback: Optional[Callable[[State, int, int], None]] = None,
    start_state: Optional[State] = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_check: Optional[CancelCheck] = None,
    trace_callback: Optional[TraceCallback] = None,
    trace_limit: int = 2_000,
    max_depth: Optional[int] = None
) -> SearchResult:
    """Solve by lowest h(n), optionally recording actual expansion decisions.

    The trace retains the first ``trace_limit`` expansions and the goal, if
    reached later. Search and solution reconstruction continue past this limit.
    Equal h values use depth, then insertion order, as in the frontier heap.
    """
    start = start_state if start_state is not None else puzzle.initial_state()
    if puzzle.is_goal(start):
        if trace_callback is not None:
            trace_callback(SearchTraceStep(
                0, 0, None, start, None, "", puzzle.heuristic(start), 0,
                1, 0, 1, 1, (), (), True,
            ))
        return SearchResult(
            "Greedy Best-First", True, [start], [], 0, 1, 1, 0.0, 0.0, 0
        )

    tracemalloc.start()
    started_at = time.perf_counter()
    parents: ParentMap = {start: (None, "")}
    depths: Dict[State, int] = {start: 0}
    visited = {start}
    node_ids = {start: 0} if trace_callback is not None else {}
    frontier: list[tuple[int, int, int, State]] = []
    heapq.heappush(frontier, (puzzle.heuristic(start), 0, 0, start))

    tie_breaker = 1
    expanded = 0
    generated = 1
    max_frontier = 1
    goal: Optional[State] = None

    def record_step(state: State, h: int, candidates: list[SearchCandidate], is_goal: bool) -> None:
        if trace_callback is None:
            return
        # Read the first five entries without sorting/scanning a large frontier.
        preview: list[FrontierEntry] = []
        pending = [(frontier[0], 0)] if frontier else []
        while pending and len(preview) < 5:
            (priority, depth, order, queued_state), index = heapq.heappop(pending)
            preview.append(FrontierEntry(order, parents[queued_state][1], priority, depth))
            for child in (index * 2 + 1, index * 2 + 2):
                if child < len(frontier):
                    heapq.heappush(pending, (frontier[child], child))
        parent, action = parents[state]
        trace_callback(SearchTraceStep(
            expanded, node_ids[state], node_ids[parent] if parent is not None else None,
            state, parent, action, h, depths[state], frontier_before, len(frontier),
            generated, max_frontier, tuple(candidates), tuple(preview), is_goal,
        ))

    while frontier and generated <= max_nodes and not (cancel_check and cancel_check()):
        frontier_before = len(frontier)
        h, _, _, state = heapq.heappop(frontier)
        expanded += 1
        if callback is not None:
            callback(state, expanded, len(frontier))
        if progress_callback is not None:
            progress_callback(state, expanded, generated, len(frontier))
        if puzzle.is_goal(state):
            goal = state
            record_step(state, h, [], True)
            break

        capture = trace_callback is not None and expanded <= trace_limit
        candidates: list[SearchCandidate] = []
        for successor, action in puzzle.successors(state):
            if cancel_check is not None and cancel_check():
                break
            if successor in visited:
                if capture:
                    candidates.append(SearchCandidate(action, None, True, node_ids[successor]))
                continue
            visited.add(successor)
            parents[successor] = (state, action)
            depths[successor] = depths[state] + 1
            generated += 1
            successor_h = puzzle.heuristic(successor)
            if trace_callback is not None:
                node_ids[successor] = tie_breaker
            if capture:
                candidates.append(SearchCandidate(action, successor_h, False, tie_breaker))
            heapq.heappush(
                frontier,
                (successor_h, depths[successor], tie_breaker, successor),
            )
            tie_breaker += 1
            if generated > max_nodes:
                break
        max_frontier = max(max_frontier, len(frontier))
        if capture:
            record_step(state, h, candidates, False)
        if progress_callback is not None:
            progress_callback(state, expanded, generated, len(frontier))

    elapsed = time.perf_counter() - started_at
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    if goal is None:
        return SearchResult(
            "Greedy Best-First", False, [], [], expanded, generated,
            max_frontier, elapsed, peak / 1024, -1,
            "cancelled" if cancel_check and cancel_check() else "node_limit" if generated > max_nodes else "exhausted",
        )

    path, actions = reconstruct_path(parents, goal)
    return SearchResult(
        "Greedy Best-First", True, path, actions, expanded, generated,
        max_frontier, elapsed, peak / 1024, len(path) - 1,
    )
