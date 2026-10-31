"""Greedy Best-First Search with priority (heuristic, depth, insertion order)."""
from __future__ import annotations

import heapq
from typing import Optional

from config import DEFAULT_MAX_NODES, DEFAULT_TRACE_LIMIT
from puzzle import PipesPuzzle
from .common import (
    CancelCheck, ExpansionCallback, ProgressCallback, SearchCandidate,
    SearchResult, State, TraceCallback,
)
from .runtime import (
    SearchMeasurement, SearchNode, build_result, is_duplicate, record_trace,
    solved_start, validate_limits,
)

HeapEntry = tuple[int, int, int, SearchNode]


def _preview(frontier: list[HeapEntry], discovered: dict[State, SearchNode]):
    """Read the five next heap entries without scanning the whole frontier."""
    pending = [(frontier[0], 0)] if frontier else []
    count = 0
    while pending and count < 5:
        (heuristic, _, _, node), index = heapq.heappop(pending)
        for child in (index * 2 + 1, index * 2 + 2):
            if child < len(frontier):
                heapq.heappush(pending, (frontier[child], child))
        if discovered[node.state] is node:
            yield node, heuristic
            count += 1


def greedy_best_first(
    puzzle: PipesPuzzle,
    max_nodes: int = DEFAULT_MAX_NODES,
    callback: Optional[ExpansionCallback] = None,
    start_state: Optional[State] = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_check: Optional[CancelCheck] = None,
    trace_callback: Optional[TraceCallback] = None,
    trace_limit: int = DEFAULT_TRACE_LIMIT,
    *,
    max_depth: Optional[int] = None,
) -> SearchResult:
    """Expand the lowest-h node; retain the first trace_limit steps and the goal.

    max_depth bounds path depth when supplied. A shorter path may then reopen
    a state, just as in DFS. Search does not guarantee the shortest solution.
    """
    validate_limits(max_nodes, max_depth, trace_limit)
    start = start_state if start_state is not None else puzzle.initial_state()
    if puzzle.is_goal(start):
        return solved_start("Greedy Best-First", puzzle, start, trace_callback)

    with SearchMeasurement() as measurement:
        root = SearchNode(start)
        discovered = {start: root}
        frontier = [(puzzle.heuristic(start), 0, 0, root)]
        expanded, generated, max_frontier = 0, 1, 1
        max_depth_reached = 0
        goal = None
        reason = "exhausted"
        depth_cutoff = False

        while frontier:
            if cancel_check is not None and cancel_check():
                reason = "cancelled"
                break
            if generated > max_nodes:
                reason = "node_limit"
                break
            frontier_before = len(frontier)
            heuristic, _, _, node = heapq.heappop(frontier)
            if discovered[node.state] is not node:
                continue
            expanded += 1
            max_depth_reached = max(max_depth_reached, node.depth)
            if callback is not None:
                callback(node.state, expanded, len(frontier))
            if progress_callback is not None:
                progress_callback(node.state, expanded, generated, len(frontier))

            is_goal = puzzle.is_goal(node.state)
            depth_limited = not is_goal and max_depth is not None and node.depth >= max_depth
            capture = trace_callback is not None and (expanded <= trace_limit or is_goal)
            candidates = []
            if is_goal:
                goal, reason = node, "solved"
            elif depth_limited:
                depth_cutoff = True
            else:
                for state, action in puzzle.successors(node.state):
                    if cancel_check is not None and cancel_check():
                        reason = "cancelled"
                        break
                    previous = discovered.get(state)
                    if is_duplicate(previous, node.depth + 1, max_depth):
                        if capture:
                            candidates.append(SearchCandidate(action, None, True, previous.node_id))
                        continue
                    child = SearchNode(state, node, action, node.depth + 1, generated)
                    discovered[state] = child
                    generated += 1
                    successor_h = puzzle.heuristic(state)
                    heapq.heappush(frontier, (successor_h, child.depth, child.node_id, child))
                    if capture:
                        candidates.append(SearchCandidate(action, successor_h, False, child.node_id))
                    if generated > max_nodes:
                        reason = "node_limit"
                        break
            max_frontier = max(max_frontier, len(frontier))
            if capture:
                record_trace(
                    puzzle, trace_callback, node, expanded=expanded, generated=generated,
                    max_frontier=max_frontier, frontier_before=frontier_before,
                    frontier_after=len(frontier), candidates=candidates, preview=_preview(frontier, discovered),
                    is_goal=is_goal, heuristic=heuristic, depth_limited=depth_limited,
                )
            if progress_callback is not None:
                progress_callback(node.state, expanded, generated, len(frontier))
            if reason in ("solved", "cancelled", "node_limit"):
                break
        if reason == "exhausted" and depth_cutoff:
            reason = "depth_limit"

    return build_result("Greedy Best-First", goal, expanded, generated, max_frontier,
                        measurement, reason, max_depth_reached)
