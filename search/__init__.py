"""Public search API; existing ``from search import ...`` imports still work."""
from .common import (
    CancelCheck, ExpansionCallback, FrontierEntry, ParentMap, ProgressCallback,
    SearchCandidate, SearchResult, SearchSolver, SearchTraceStep, State,
    TraceCallback, reconstruct_path, validate_solution,
)
from .dfs import depth_first_search
from .greedy import greedy_best_first
from .registry import ALGORITHMS, SearchAlgorithm, get_algorithm

__all__ = [
    "ALGORITHMS", "CancelCheck", "ExpansionCallback", "FrontierEntry", "ParentMap",
    "ProgressCallback", "SearchAlgorithm", "SearchCandidate", "SearchResult",
    "SearchSolver", "SearchTraceStep", "State", "TraceCallback",
    "depth_first_search", "get_algorithm", "greedy_best_first", "reconstruct_path", "validate_solution",
]
