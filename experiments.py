"""Generate paired inputs and benchmark registered solvers in fresh processes."""
from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
import statistics
import subprocess
import sys

from config import BASE_DIR, EXPERIMENT_MAX_NODES, EXPERIMENT_SEEDS, PUZZLE_PRESETS, default_max_depth
from generator import make_random_puzzle, save_puzzle
from puzzle import PipesPuzzle
from search import get_algorithm, validate_solution

RAW_FIELDS = (
    "Kích thước", "Lượt", "Seed", "File puzzle", "Thuật toán", "Kết quả", "Lý do dừng",
    "Expanded states", "Generated states", "Solution depth", "Maximum frontier size", "Max depth reached",
    "Thời gian (ms)", "Bộ nhớ (KiB)", "Lỗi",
)


@dataclass(frozen=True)
class ExperimentConfig:
    sizes: tuple[int, ...] = tuple(preset.size for preset in PUZZLE_PRESETS)
    seeds: tuple[int, ...] = EXPERIMENT_SEEDS
    algorithms: tuple[str, ...] = ("dfs", "greedy")
    max_nodes: int = EXPERIMENT_MAX_NODES
    max_depth: int | None = None
    puzzle_dir: Path = BASE_DIR / "experiment_puzzles"
    output_dir: Path = BASE_DIR / "experiment_results"

    def validate(self) -> None:
        if not self.sizes or any(size < 3 for size in self.sizes):
            raise ValueError("Experiment sizes must be at least 3")
        if not self.seeds or not self.algorithms:
            raise ValueError("Experiments need at least one seed and algorithm")
        if self.max_nodes < 1 or (self.max_depth is not None and self.max_depth < 0):
            raise ValueError("max_nodes must be positive and max_depth nonnegative")
        for algorithm in self.algorithms:
            get_algorithm(algorithm)

    def depth_for(self, size: int, algorithm: str = "dfs") -> int | None:
        if self.max_depth is not None:
            return self.max_depth
        return default_max_depth(size, size) if algorithm == "dfs" else None


def measure(puzzle_path: str | Path, algorithm: str, max_nodes: int, max_depth: int | None) -> dict:
    puzzle = PipesPuzzle.from_json(str(puzzle_path))
    selected = get_algorithm(algorithm)
    result = selected.solver(puzzle, max_nodes=max_nodes, max_depth=max_depth)
    valid = not result.found or validate_solution(puzzle, result)
    if not valid:
        raise ValueError(f"{selected.label} returned an invalid solution for {puzzle_path}")
    return {
        "algorithm": result.algorithm, "found": result.found,
        "termination_reason": result.termination_reason, "depth": result.depth,
        "nodes_expanded": result.nodes_expanded, "nodes_generated": result.nodes_generated,
        "max_frontier": result.max_frontier, "time_ms": result.time_sec * 1000,
        "max_depth_reached": result.max_depth_reached,
        "peak_kib": result.peak_memory_kb, "is_valid": valid,
    }


def format_stat(mean_val: float, std_val: float, is_int: bool = False, dp: int = 1) -> str:
    if std_val == 0:
        return str(round(mean_val)) if is_int else f"{mean_val:.{dp}f}"
    digits = 1 if is_int else dp
    return f"{mean_val:.{digits}f} ± {std_val:.{digits}f}"


def summarize(size: int, results: list[dict | None], max_depth: int | None, rotatable: list[int]) -> dict:
    valid = [result for result in results if result is not None]
    solved = [result for result in valid if result["found"]]
    if len(solved) == len(results):
        status = "Đạt"
    elif solved:
        status = "Đạt một phần"
    else:
        status = "Không đạt" if len(valid) == len(results) else "Lỗi"

    def stat(values, *, is_int=False, dp=1):
        return format_stat(statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0,
                           is_int=is_int, dp=dp) if values else "—"

    depth = stat([result["depth"] for result in solved], is_int=True)
    if solved and len(solved) != len(results):
        depth += " *"
    return {
        "Kích thước": f"{size}x{size}", "Số ô (N)": size * size,
        "Ô xoay": stat(rotatable, is_int=True), "max_depth": max_depth,
        "Kết quả": status, "Số lượt": len(results),
        "Số lượt đạt": len(solved), "Số lượt lỗi": len(results) - len(valid),
        "Expanded states": stat([result["nodes_expanded"] for result in valid], is_int=True),
        "Generated states": stat([result["nodes_generated"] for result in valid], is_int=True),
        "Solution depth": depth,
        "Maximum frontier size": stat([result["max_frontier"] for result in valid], is_int=True),
        "Max depth reached": stat([result["max_depth_reached"] for result in valid], is_int=True),
        "Thời gian (ms)": stat([result["time_ms"] for result in valid], dp=2),
        "Bộ nhớ (KiB)": stat([result["peak_kib"] for result in valid]),
    }


def write_csv(path: Path, rows: list[dict], fields=None) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_experiments(config: ExperimentConfig = ExperimentConfig()) -> None:
    config.validate()
    config.puzzle_dir.mkdir(parents=True, exist_ok=True)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    cases = {}
    for size in config.sizes:
        for run, seed in enumerate(config.seeds, 1):
            puzzle, _ = make_random_puzzle(size, size, seed=seed, sparse=True)
            path = config.puzzle_dir / f"puzzle_{size}x{size}_run{run}_seed{seed}.json"
            save_puzzle(puzzle, str(path))
            movable = sum(not cell.locked and cell.type not in ("EMPTY", "CROSS") for cell in puzzle.cells)
            cases[size, run] = path, movable

    for algorithm in config.algorithms:
        print(f"{get_algorithm(algorithm).label}: {len(config.seeds)} lượt / kích thước", flush=True)
        raw, summaries = [], []
        for size in config.sizes:
            results, movable_counts = [], []
            for run, seed in enumerate(config.seeds, 1):
                path, movable = cases[size, run]
                movable_counts.append(movable)
                row = dict.fromkeys(RAW_FIELDS, "")
                row.update({"Kích thước": f"{size}x{size}", "Lượt": run, "Seed": seed,
                            "File puzzle": path.name, "Thuật toán": algorithm})
                command = [sys.executable, "-B", str(BASE_DIR / "benchmark.py"), "--worker",
                           "--algorithm", algorithm, "--puzzle-path", str(path),
                           "--max-nodes", str(config.max_nodes)]
                depth_limit = config.depth_for(size, algorithm)
                if depth_limit is not None:
                    command.extend(("--max-depth", str(depth_limit)))
                try:
                    process = subprocess.run(command, capture_output=True, text=True,
                                             encoding="utf-8", timeout=300, check=True)
                    result = json.loads(process.stdout)
                    if not result["is_valid"]:
                        raise ValueError("Worker returned an invalid solution")
                except (subprocess.SubprocessError, ValueError) as error:
                    results.append(None)
                    row.update({"Kết quả": "Lỗi", "Lỗi": str(error)})
                    raw.append(row)
                    print(f"{size}x{size} seed={seed}: {error}", file=sys.stderr, flush=True)
                    continue
                results.append(result)
                row.update({
                    "Kết quả": "Đạt" if result["found"] else "Không đạt",
                    "Lý do dừng": result["termination_reason"],
                    "Expanded states": result["nodes_expanded"], "Generated states": result["nodes_generated"],
                    "Solution depth": result["depth"] if result["found"] else "—",
                    "Maximum frontier size": result["max_frontier"],
                    "Max depth reached": result["max_depth_reached"],
                    "Thời gian (ms)": f"{result['time_ms']:.2f}", "Bộ nhớ (KiB)": f"{result['peak_kib']:.1f}",
                })
                raw.append(row)
                print(f"{size}x{size} seed={seed}: {row['Kết quả']} ({result['termination_reason']})", flush=True)
            summaries.append(summarize(size, results, config.depth_for(size, algorithm), movable_counts))
        write_csv(config.output_dir / f"benchmark_{algorithm}_raw.csv", raw, RAW_FIELDS)
        write_csv(config.output_dir / f"benchmark_{algorithm}_summary.csv", summaries)
