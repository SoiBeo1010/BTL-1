"""Algorithm metadata shared by the dashboard and benchmark."""
from dataclasses import dataclass

from . import dfs
from .common import SearchSolver
from .greedy import greedy_best_first


@dataclass(frozen=True)
class SearchAlgorithm:
    key: str
    label: str
    solver: SearchSolver
    available: bool = True
    uses_heuristic: bool = True


ALGORITHMS = {
    "greedy": SearchAlgorithm("greedy", "Greedy Best-First", greedy_best_first),
    "dfs": SearchAlgorithm(
        "dfs", "Depth-First Search", dfs.depth_first_search,
        available=dfs.IMPLEMENTED, uses_heuristic=False,
    ),
}


def get_algorithm(key: str) -> SearchAlgorithm:
    """Resolve a usable solver and reject unfinished algorithms before running."""
    if key not in ALGORITHMS:
        raise ValueError(f"Thuật toán không hợp lệ: {key!r}. Chọn: {', '.join(ALGORITHMS)}.")
    algorithm = ALGORITHMS[key]
    if not algorithm.available:
        raise NotImplementedError(f"{algorithm.label} chưa sẵn sàng. Xem docs/adding_dfs.md.")
    return algorithm
