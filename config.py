"""Puzzle presets and search defaults shared by the UI and benchmarks."""
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MAX_NODES = 500_000
DEFAULT_TRACE_LIMIT = 2_000
EXPERIMENT_MAX_NODES = 10_000
EXPERIMENT_SEEDS = (42, 123, 999)


@dataclass(frozen=True, slots=True)
class PuzzlePreset:
    key: str
    filename: str
    label: str
    size: int
    description: str

    @property
    def path(self) -> Path:
        return BASE_DIR / "puzzles" / f"{self.filename}.json"


PUZZLE_PRESETS = (
    PuzzlePreset("1", "tiny_3x3", "TINY", 3, "Mạng nhỏ"),
    PuzzlePreset("2", "easy_4x4", "EASY", 4, "Mạng cơ bản"),
    PuzzlePreset("3", "medium_5x5", "MEDIUM", 5, "Mạng nhiều nhánh"),
    PuzzlePreset("4", "hard_6x6", "HARD", 6, "Mạng nhiều vòng"),
    PuzzlePreset("5", "large_7x7", "LARGE", 7, "Mạng lớn"),
)


def default_max_depth(rows: int, cols: int) -> int:
    """Return ceil(1.5 * number of cells), shared by UI and experiments."""
    return (3 * rows * cols + 1) // 2
