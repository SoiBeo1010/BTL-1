"""Blind DFS: visit successors in generation order using a LIFO stack.

Children are pushed in reverse order, so the first generated child is visited
first. Heuristic values are only computed for trace display.
"""
from __future__ import annotations

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

IMPLEMENTED = True


def depth_first_search(
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
    """Search without heuristic guidance, optionally limiting path depth.

    A shallower path can reopen a state when max_depth is set. Each accepted
    path receives its own node ID so earlier trace parents remain unchanged.
    Like GBFS, the node budget stops generation after max_nodes + 1 nodes.
    """
    validate_limits(max_nodes, max_depth, trace_limit)
    start = start_state if start_state is not None else puzzle.initial_state()
    if puzzle.is_goal(start):
        return solved_start("Depth-First Search", puzzle, start, trace_callback)

    with SearchMeasurement() as measurement:
        root = SearchNode(start)
        discovered = {start: root}
        frontier = [root]
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
            node = frontier.pop()
            if discovered[node.state] is not node:
                continue  # A shallower path replaced this queued entry.
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
            children = []
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
                    children.append(child)
                    if capture:
                        candidates.append(SearchCandidate(action, puzzle.heuristic(state), False, child.node_id))
                    if generated > max_nodes:
                        reason = "node_limit"
                        break
                frontier.extend(reversed(children))
            max_frontier = max(max_frontier, len(frontier))
            if capture:
                record_trace(
                    puzzle, trace_callback, node, expanded=expanded, generated=generated,
                    max_frontier=max_frontier, frontier_before=frontier_before,
                    frontier_after=len(frontier), candidates=candidates,
                    preview=((queued, puzzle.heuristic(queued.state)) for queued in reversed(frontier[-5:])),
                    is_goal=is_goal, depth_limited=depth_limited,
                )
            if progress_callback is not None:
                progress_callback(node.state, expanded, generated, len(frontier))
            if reason in ("solved", "cancelled", "node_limit"):
                break
        if reason == "exhausted" and depth_cutoff:
            reason = "depth_limit"

    return build_result("Depth-First Search", goal, expanded, generated, max_frontier,
                        measurement, reason, max_depth_reached)
