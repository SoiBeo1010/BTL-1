"""Stack-based DFS with the shared UI trace and cancellation contract."""
from __future__ import annotations

import time
import tracemalloc
from typing import Optional

from puzzle import PipesPuzzle
from .common import (
    CancelCheck, ExpansionCallback, ProgressCallback, SearchResult, State,
    TraceCallback, FrontierEntry, SearchCandidate, SearchTraceStep, reconstruct_path,
)

IMPLEMENTED = True


def depth_first_search(
    puzzle: PipesPuzzle,
    max_nodes: int = 500_000,
    callback: Optional[ExpansionCallback] = None,
    start_state: Optional[State] = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_check: Optional[CancelCheck] = None,
    trace_callback: Optional[TraceCallback] = None,
    trace_limit: int = 2_000,
) -> SearchResult:
    """Push successors in generation order; the last new successor is next.

    Mark states visited when pushed. Heuristic values are only computed for
    trace display and never affect the LIFO traversal or duplicate handling.
    """
    start = start_state if start_state is not None else puzzle.initial_state()
    if puzzle.is_goal(start):
        if trace_callback is not None:
            trace_callback(SearchTraceStep(
                0, 0, None, start, None, "", puzzle.heuristic(start), 0,
                1, 0, 1, 1, (), (), True,
            ))
        return SearchResult("Depth-First Search", True, [start], [], 0, 1, 1, 0.0, 0.0, 0)

    owns_tracing = not tracemalloc.is_tracing()
    if owns_tracing:
        tracemalloc.start()
    started_at = time.perf_counter()
    parents = {start: (None, "")}
    depths = {start: 0}
    node_ids = {start: 0}
    frontier = [start]
    expanded, generated, max_frontier = 0, 1, 1
    goal = None
    reason = "exhausted"

    def record(state, candidates, is_goal, frontier_before):
        if trace_callback is None:
            return
        parent, action = parents[state]
        preview = tuple(
            FrontierEntry(node_ids[queued], parents[queued][1],
                          puzzle.heuristic(queued), depths[queued])
            for queued in reversed(frontier[-5:])
        )
        trace_callback(SearchTraceStep(
            expanded, node_ids[state], node_ids[parent] if parent is not None else None,
            state, parent, action, puzzle.heuristic(state), depths[state],
            frontier_before, len(frontier), generated, max_frontier,
            tuple(candidates), preview, is_goal,
        ))

    try:
        while frontier:
            if cancel_check is not None and cancel_check():
                reason = "cancelled"
                break
            if generated > max_nodes:
                reason = "node_limit"
                break
            frontier_before = len(frontier)
            state = frontier.pop()
            expanded += 1
            if callback is not None:
                callback(state, expanded, len(frontier))
            if progress_callback is not None:
                progress_callback(state, expanded, generated, len(frontier))
            if puzzle.is_goal(state):
                goal = state
                reason = "solved"
                record(state, [], True, frontier_before)
                break

            capture = trace_callback is not None and expanded <= trace_limit
            candidates = []
            for successor, action in puzzle.successors(state):
                if cancel_check is not None and cancel_check():
                    reason = "cancelled"
                    break
                if successor in node_ids:
                    if capture:
                        candidates.append(SearchCandidate(action, None, True, node_ids[successor]))
                    continue
                node_ids[successor] = generated
                parents[successor] = (state, action)
                depths[successor] = depths[state] + 1
                generated += 1
                frontier.append(successor)
                if capture:
                    candidates.append(SearchCandidate(
                        action, puzzle.heuristic(successor), False, node_ids[successor],
                    ))
                if generated > max_nodes:
                    reason = "node_limit"
                    break
            max_frontier = max(max_frontier, len(frontier))
            if capture:
                record(state, candidates, False, frontier_before)
            if progress_callback is not None:
                progress_callback(state, expanded, generated, len(frontier))
            if reason in ("cancelled", "node_limit"):
                break
        elapsed = time.perf_counter() - started_at
        _, peak = tracemalloc.get_traced_memory()
    finally:
        if owns_tracing:
            tracemalloc.stop()

    if goal is None:
        return SearchResult(
            "Depth-First Search", False, [], [], expanded, generated,
            max_frontier, elapsed, peak / 1024, -1, reason,
        )
    path, actions = reconstruct_path(parents, goal)
    return SearchResult(
        "Depth-First Search", True, path, actions, expanded, generated,
        max_frontier, elapsed, peak / 1024, len(path) - 1, "solved",
    )
