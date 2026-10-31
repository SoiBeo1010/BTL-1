"""Shared search types, callbacks and solution reconstruction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Protocol, Tuple

from puzzle import PipesPuzzle
from config import DEFAULT_MAX_NODES, DEFAULT_TRACE_LIMIT

State = Tuple[int, ...]
ParentMap = Dict[State, Tuple[Optional[State], str]]
ProgressCallback = Callable[[State, int, int, int], None]
CancelCheck = Callable[[], bool]
ExpansionCallback = Callable[[State, int, int], None]


@dataclass(frozen=True, slots=True)
class SearchCandidate:
    action: str
    heuristic: Optional[int]
    duplicate: bool
    node_id: int


@dataclass(frozen=True, slots=True)
class FrontierEntry:
    """A queued node; previews list the next node to expand first."""

    node_id: int
    action: str
    heuristic: int
    depth: int


@dataclass(frozen=True, slots=True)
class SearchTraceStep:
    """An actual expansion, with its parent and frontier after processing."""

    number: int
    node_id: int
    parent_id: Optional[int]
    state: State
    parent_state: Optional[State]
    action: str
    heuristic: int
    depth: int
    frontier_before: int
    frontier_after: int
    generated: int
    max_frontier: int
    candidates: tuple[SearchCandidate, ...]
    frontier_preview: tuple[FrontierEntry, ...]
    is_goal: bool


TraceCallback = Callable[[SearchTraceStep], None]


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
    termination_reason: str = "solved"
    max_depth_reached: int = 0  # Largest depth actually expanded, including the goal.


class SearchSolver(Protocol):
    """Signature implemented by every solver used by the UI and benchmark."""

    def __call__(
        self,
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
    ) -> SearchResult: ...


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


def validate_solution(puzzle: PipesPuzzle, result: SearchResult, start: Optional[State] = None) -> bool:
    """Check a reported solution using the model's actual legal transitions."""
    expected_start = puzzle.initial_state() if start is None else start
    return (
        result.found and bool(result.path)
        and result.path[0] == expected_start
        and puzzle.is_goal(result.path[-1])
        and result.depth == len(result.actions) == len(result.path) - 1
        and all(
            any(state == after and action == expected for state, action in puzzle.successors(before))
            for before, after, expected in zip(result.path, result.path[1:], result.actions)
        )
    )
