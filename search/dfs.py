"""DFS integration point reserved for the team member implementing it.

Follow docs/adding_dfs.md and set IMPLEMENTED to True after implementation.
"""
from __future__ import annotations

from typing import Optional

from puzzle import PipesPuzzle
from .common import (
    CancelCheck, ExpansionCallback, ProgressCallback, SearchResult, State,
    TraceCallback,
)

IMPLEMENTED = False


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
    """Implement stack-based graph search using the shared solver contract."""
    raise NotImplementedError("DFS chưa được triển khai. Xem docs/adding_dfs.md.")
