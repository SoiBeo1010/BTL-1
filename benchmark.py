"""Benchmark Greedy Best-First Search on the sample puzzles."""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from puzzle import PipesPuzzle
from search import greedy_best_first

PUZZLES = [
    "puzzles/tiny_3x3.json",
    "puzzles/easy_4x4.json",
    "puzzles/medium_5x5.json",
    "puzzles/hard_6x6.json",
]


def run() -> None:
    rows = []
    for path in PUZZLES:
        name = os.path.basename(path).replace(".json", "")
        puzzle = PipesPuzzle.from_json(path)
        result = greedy_best_first(puzzle, max_nodes=500_000)
        print(
            f"{name:14s} found={result.found} depth={result.depth} "
            f"expanded={result.nodes_expanded} generated={result.nodes_generated} "
            f"frontier={result.max_frontier} time={result.time_sec:.4f}s "
            f"mem={result.peak_memory_kb:.1f}KB"
        )
        rows.append(
            (
                name,
                result.found,
                result.depth,
                result.nodes_expanded,
                result.nodes_generated,
                result.max_frontier,
                result.time_sec,
                result.peak_memory_kb,
            )
        )

    with open("benchmark.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "puzzle",
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
    print("Saved benchmark.csv")


if __name__ == "__main__":
    run()
