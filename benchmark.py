"""Benchmark fixture puzzles or run paired experiments in fresh processes."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

from config import (
    BASE_DIR, DEFAULT_MAX_NODES, EXPERIMENT_MAX_NODES, EXPERIMENT_SEEDS,
    PUZZLE_PRESETS, default_max_depth,
)
from experiments import ExperimentConfig, measure, run_experiments
from puzzle import PipesPuzzle
from search import ALGORITHMS, get_algorithm, validate_solution

PUZZLES = [str(preset.path.relative_to(BASE_DIR)) for preset in PUZZLE_PRESETS]
CSV_FIELDS = ("puzzle", "algorithm", "found", "depth", "expanded", "generated",
              "max_frontier", "time_s", "peak_mem_KB", "termination_reason", "max_depth_reached")


def run(algorithm: str = "greedy", max_nodes: int = DEFAULT_MAX_NODES,
        output: str = "benchmark.csv", *, max_depth: int | None = None) -> None:
    """Benchmark JSON fixtures through the same registry used by the UI."""
    selected = get_algorithm(algorithm)
    rows = []
    for filename in PUZZLES:
        path = BASE_DIR / filename
        puzzle = PipesPuzzle.from_json(str(path))
        result = selected.solver(puzzle, max_nodes=max_nodes, max_depth=max_depth)
        if result.found and not validate_solution(puzzle, result):
            raise ValueError(f"{selected.label} returned an invalid solution for {path}")
        print(f"{selected.key:6s} {path.stem:14s} found={result.found} depth={result.depth} "
              f"expanded={result.nodes_expanded} generated={result.nodes_generated} "
              f"frontier={result.max_frontier} time={result.time_sec:.4f}s "
              f"mem={result.peak_memory_kb:.1f}KiB")
        rows.append(dict(zip(CSV_FIELDS, (
            path.stem, result.algorithm, result.found, result.depth, result.nodes_expanded,
            result.nodes_generated, result.max_frontier, result.time_sec,
            result.peak_memory_kb, result.termination_reason, result.max_depth_reached,
        ))))
    with open(output, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", action="store_true", help="Compare generated puzzles using fresh processes")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--algorithm", choices=ALGORITHMS)
    parser.add_argument("--puzzle-path", type=Path)
    parser.add_argument("--max-nodes", type=int)
    parser.add_argument("--max-depth", type=int)
    parser.add_argument("--output", default="benchmark.csv")
    parser.add_argument("--output-dir", type=Path, default=BASE_DIR / "experiment_results")
    parser.add_argument("--puzzle-dir", type=Path, default=BASE_DIR / "experiment_puzzles")
    parser.add_argument("--sizes", nargs="+", type=int, default=[preset.size for preset in PUZZLE_PRESETS])
    parser.add_argument("--seeds", nargs="+", type=int, default=list(EXPERIMENT_SEEDS))
    args = parser.parse_args()
    if args.max_nodes is not None and args.max_nodes < 1:
        parser.error("--max-nodes must be positive")
    if args.max_depth is not None and args.max_depth < 0:
        parser.error("--max-depth must be nonnegative")
    try:
        if args.worker:
            if not args.algorithm or not args.puzzle_path:
                parser.error("--worker requires --algorithm and --puzzle-path")
            depth = args.max_depth
            if depth is None and args.algorithm == "dfs":
                puzzle = PipesPuzzle.from_json(str(args.puzzle_path))
                depth = default_max_depth(puzzle.rows, puzzle.cols)
            print(json.dumps(measure(args.puzzle_path, args.algorithm,
                                     args.max_nodes or EXPERIMENT_MAX_NODES, depth)))
        elif args.experiment:
            run_experiments(ExperimentConfig(
                sizes=tuple(args.sizes), seeds=tuple(args.seeds),
                algorithms=(args.algorithm,) if args.algorithm else ("dfs", "greedy"),
                max_nodes=args.max_nodes or EXPERIMENT_MAX_NODES, max_depth=args.max_depth,
                output_dir=args.output_dir, puzzle_dir=args.puzzle_dir,
            ))
        else:
            run(args.algorithm or "greedy", args.max_nodes or DEFAULT_MAX_NODES,
                args.output, max_depth=args.max_depth)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    main()

