"""Check subprocess integration, valid paths, statistics and failure handling."""
import contextlib
import csv
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from config import default_max_depth
from experiments import ExperimentConfig, run_experiments, summarize
from search import SearchResult, validate_solution
from puzzle import Cell, PipesPuzzle


def measurement(found=True):
    return {"found": found, "termination_reason": "solved" if found else "node_limit",
            "depth": 3 if found else -1, "nodes_expanded": 5, "nodes_generated": 9,
            "max_frontier": 6, "max_depth_reached": 3, "time_ms": 1.0, "peak_kib": 2.0}


class ExperimentTests(unittest.TestCase):
    def test_single_success_depth_has_no_sample_stdev_and_errors_are_counted(self):
        summary = summarize(3, [measurement(), measurement(False), None], 14, [8, 8, 8])
        self.assertEqual(summary["Solution depth"], "3 *")
        self.assertEqual(summary["Kết quả"], "Đạt một phần")
        self.assertEqual(summary["Số lượt đạt"], 1)
        self.assertEqual(summary["Số lượt lỗi"], 1)

    def test_worker_failure_is_kept_in_csv_without_reporting_full_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = ExperimentConfig(sizes=(3,), seeds=(42,), algorithms=("greedy",),
                                      output_dir=root / "results", puzzle_dir=root / "puzzles")
            with (patch("experiments.subprocess.run", side_effect=subprocess.TimeoutExpired("worker", 1)),
                  contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO())):
                run_experiments(config)
            with (config.output_dir / "benchmark_greedy_raw.csv").open(encoding="utf-8-sig") as stream:
                raw = list(csv.DictReader(stream))
            with (config.output_dir / "benchmark_greedy_summary.csv").open(encoding="utf-8-sig") as stream:
                summary = list(csv.DictReader(stream))
            self.assertEqual(raw[0]["Kết quả"], "Lỗi")
            self.assertEqual(summary[0]["Số lượt lỗi"], "1")
            self.assertEqual(summary[0]["Kết quả"], "Lỗi")

    def test_generated_experiment_runs_both_registered_solvers_in_fresh_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = ExperimentConfig(sizes=(3,), seeds=(42,), max_nodes=100,
                                      output_dir=root / "results", puzzle_dir=root / "puzzles")
            with contextlib.redirect_stdout(io.StringIO()):
                run_experiments(config)
            for algorithm in config.algorithms:
                with (config.output_dir / f"benchmark_{algorithm}_raw.csv").open(encoding="utf-8-sig") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["Thuật toán"], algorithm)
                self.assertEqual(rows[0]["Lý do dừng"], "solved" if algorithm == "greedy" else "node_limit")
                if algorithm == "greedy":
                    self.assertEqual(rows[0]["Solution depth"], "4")
                self.assertEqual(rows[0]["Lỗi"], "")
                with (config.output_dir / f"benchmark_{algorithm}_summary.csv").open(encoding="utf-8-sig") as stream:
                    summary = next(csv.DictReader(stream))
                self.assertEqual(summary["max_depth"], str(default_max_depth(3, 3)) if algorithm == "dfs" else "")

    def test_greedy_has_no_default_depth_limit(self):
        config = ExperimentConfig()
        self.assertIsNone(config.depth_for(3, "greedy"))
        self.assertEqual(config.depth_for(3, "dfs"), 14)
        self.assertEqual(ExperimentConfig(max_depth=7).depth_for(3, "greedy"), 7)

    def test_validation_rejects_wrong_start_and_rotation_of_locked_cell(self):
        puzzle = PipesPuzzle(1, 2, [Cell("END", 1, True), Cell("END", 3)], root_index=0)
        wrong_start = SearchResult("probe", True, [(1, 1), (1, 3)], ["R1+2"], 0, 0, 0, 0, 0, 1)
        self.assertFalse(validate_solution(puzzle, wrong_start))
        illegal_move = SearchResult("probe", True, [(3, 3), (1, 3)], ["R0+2"], 0, 0, 0, 0, 0, 1)
        self.assertFalse(validate_solution(puzzle, illegal_move, start=(3, 3)))
