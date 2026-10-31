"""Depth-First Search solver for the Pipes puzzle.

Uses a stack (LIFO) for graph-search with cycle detection via a visited set.
Successors are generated from top-left to bottom-right (90° → 180° → 270°)
and pushed onto the LIFO stack in reverse order.  This ensures that the
popped order is strictly left-to-right, top-to-bottom, and 90° before 180°
and 270° (i.e. cell (1, 1) 90° first, then cell (1, 2) 90°, etc.).

The heuristic h(n) is recorded in each trace step for visualisation/display
purposes only, and is never used to select the next node to expand.
"""
from __future__ import annotations

import time
import tracemalloc
from typing import Dict, Optional

from puzzle import PipesPuzzle
from .common import (
    CancelCheck, ExpansionCallback, FrontierEntry, ParentMap, ProgressCallback,
    SearchCandidate, SearchResult, SearchTraceStep, State, TraceCallback,
    reconstruct_path,
)

IMPLEMENTED = True
IMPLEMENTED = True


def depth_first_search(
    puzzle: PipesPuzzle,
    max_nodes: int = 500_000,
    max_depth: Optional[int] = None,
    callback: Optional[ExpansionCallback] = None,
    start_state: Optional[State] = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_check: Optional[CancelCheck] = None,
    trace_callback: Optional[TraceCallback] = None,
    trace_limit: int = 2_000,
) -> SearchResult:
    """Solve using Blind Depth-First Search (no heuristic guidance).

    Uses a LIFO stack.  Nodes are expanded in last-in-first-out order.
    Successors are pushed in reverse so that cell (1, 1) at 90° is popped
    first, followed by cell (1, 2) at 90°, matching natural reading order.

    Parameters:
        puzzle: PipesPuzzle instance to solve.
        max_nodes: Maximum number of states generated before stopping.
        max_depth: Optional maximum search depth cutoff.
        callback: Optional legacy expansion callback (state, expanded, frontier_size).
        start_state: Optional override for the starting board state.
        progress_callback: Optional UI progress callback.
        cancel_check: Optional callable returning True to abort search early.
        trace_callback: Optional callback receiving SearchTraceStep instances.
        trace_limit: Maximum number of expansion steps to record for UI playback.
    """
    start = start_state if start_state is not None else puzzle.initial_state()

    # Edge case: start state is already a solution.
    if puzzle.is_goal(start):
        if trace_callback is not None:
            trace_callback(SearchTraceStep(
                0, 0, None, start, None, "",
                puzzle.heuristic(start), 0,
                1, 0, 1, 1, (), (), True,
            ))
        return SearchResult(
            "Depth-First Search", True, [start], [], 0, 1, 1, 0.0, 0.0, 0
        )

    tracemalloc.start()
    started_at = time.perf_counter()

    parents: ParentMap = {start: (None, "")}
    depths: Dict[State, int] = {start: 0}
    visited: set[State] = {start}
    # node_ids tracks the sequential generation order for trace display.
    node_ids: Dict[State, int] = {start: 0} if trace_callback is not None else {}

    # Stack entries: (depth, generation_order, state)
    frontier: list[tuple[int, int, State]] = [(0, 0, start)]

    tie_breaker = 1
    expanded = 0
    generated = 1
    max_frontier = 1
    goal: Optional[State] = None

    def record_step(
        state: State,
        h: int,
        candidates: list[SearchCandidate],
        is_goal: bool,
    ) -> None:
        """Emit one SearchTraceStep; no-op when trace_callback is None."""
        if trace_callback is None:
            return
        # Preview the top-5 of the stack (last 5 elements = next to pop).
        preview: list[FrontierEntry] = []
        for i in range(max(0, len(frontier) - 5), len(frontier)):
            d_i, order_i, queued_state = frontier[i]
            preview.append(FrontierEntry(order_i, parents[queued_state][1], 0, d_i))
        preview.reverse()  # first entry is the very next node to expand
        parent, action = parents[state]
        trace_callback(SearchTraceStep(
            expanded,
            node_ids[state],
            node_ids[parent] if parent is not None else None,
            state,
            parent,
            action,
            h,
            depths[state],
            frontier_before,
            len(frontier),
            generated,
            max_frontier,
            tuple(candidates),
            tuple(preview),
            is_goal,
        ))

    while frontier and generated <= max_nodes and not (cancel_check and cancel_check()):
        frontier_before = len(frontier)
        depth, _, state = frontier.pop()   # LIFO: take from the top of the stack
        expanded += 1

        if callback is not None:
            callback(state, expanded, len(frontier))
        if progress_callback is not None:
            progress_callback(state, expanded, generated, len(frontier))

        # Only compute h when the trace is being recorded (expensive call).
        capture = trace_callback is not None and expanded <= trace_limit
        h = puzzle.heuristic(state) if capture else 0

        if puzzle.is_goal(state):
            goal = state
            record_step(state, h, [], True)
            break

        # Giới hạn độ sâu cắt tỉa
        if max_depth is not None and depth >= max_depth:
            if capture:
                record_step(state, h, [], False)
            continue

        candidates: list[SearchCandidate] = []
        to_push: list[tuple[int, int, State]] = []

        # puzzle.successors sinh từ trái sang phải, từ trên xuống dưới, 90° -> 180° -> 270°
        for successor, action in puzzle.successors(state):
            if cancel_check is not None and cancel_check():
                break
            if successor in visited:
                if capture:
                    candidates.append(
                        SearchCandidate(action, None, True, node_ids.get(successor, -1))
                    )
                continue

            visited.add(successor)
            parents[successor] = (state, action)
            depths[successor] = depth + 1
            generated += 1
            if trace_callback is not None:
                node_ids[successor] = tie_breaker
            successor_h = puzzle.heuristic(successor) if capture else None
            if capture:
                candidates.append(
                    SearchCandidate(action, successor_h, False, tie_breaker)
                )
            to_push.append((depth + 1, tie_breaker, successor))
            tie_breaker += 1

            if generated > max_nodes:
                break

        # Đẩy vào ngăn xếp LIFO theo thứ tự ngược lại (đẩy (3, 3) 270° trước, (1, 1) 90° sau cùng)
        # để khi pop() từ đỉnh stack, ô (1, 1) xoay 90° sẽ được lấy ra duyệt đầu tiên.
        for item in reversed(to_push):
            frontier.append(item)

        max_frontier = max(max_frontier, len(frontier))
        if capture:
            record_step(state, h, candidates, False)
        if progress_callback is not None:
            progress_callback(state, expanded, generated, len(frontier))

    elapsed = time.perf_counter() - started_at
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    if goal is None:
        if cancel_check and cancel_check():
            reason = "cancelled"
        elif generated > max_nodes:
            reason = "node_limit"
        else:
            reason = "exhausted"
        return SearchResult(
            "Depth-First Search", False, [], [], expanded, generated,
            max_frontier, elapsed, peak / 1024, -1, reason,
        )

    path, actions = reconstruct_path(parents, goal)
    return SearchResult(
        "Depth-First Search", True, path, actions, expanded, generated,
        max_frontier, elapsed, peak / 1024, len(path) - 1,
    )
