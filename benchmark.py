"""Benchmark a registered search algorithm on the sample puzzles."""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from puzzle import PipesPuzzle
from search import ALGORITHMS, get_algorithm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PUZZLES = [
    "puzzles/tiny_3x3.json",
    "puzzles/easy_4x4.json",
    "puzzles/medium_5x5.json",
    "puzzles/hard_6x6.json",
    "puzzles/large_7x7.json",
]


def run(algorithm: str = "greedy", max_nodes: int = 500_000, output: str = "benchmark.csv") -> None:
    selected = get_algorithm(algorithm)
    rows = []
    for path in PUZZLES:
        name = os.path.basename(path).replace(".json", "")
        puzzle = PipesPuzzle.from_json(os.path.join(BASE_DIR, path))
        result = selected.solver(puzzle, max_nodes=max_nodes)
        print(
            f"{selected.key:6s} {name:14s} found={result.found} depth={result.depth} "
            f"expanded={result.nodes_expanded} generated={result.nodes_generated} "
            f"frontier={result.max_frontier} time={result.time_sec:.4f}s "
            f"mem={result.peak_memory_kb:.1f}KB"
        )
        rows.append(
            (
                name,
                result.algorithm,
                result.found,
                result.depth,
                result.nodes_expanded,
                result.nodes_generated,
                result.max_frontier,
                result.time_sec,
                result.peak_memory_kb,
            )
        )

    with open(output, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "puzzle",
                "algorithm",
                "found",
                "depth",
                "expanded",
                "generated",
                "max_frontier",
                "time_s",
                "peak_mem_KB",
            ]
        )
        writer.writerows(rows)
    print(f"Saved {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithm", choices=ALGORITHMS, default="greedy")
    parser.add_argument("--max-nodes", type=int, default=500_000)
    parser.add_argument("--output", default="benchmark.csv")
    args = parser.parse_args()
    if args.max_nodes < 1:
        parser.error("--max-nodes phải lớn hơn 0")
    try:
        get_algorithm(args.algorithm)
    except (ValueError, NotImplementedError) as error:
        parser.error(str(error))
    run(args.algorithm, args.max_nodes, args.output)


if __name__ == "__main__":
    main()
