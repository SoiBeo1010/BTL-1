import contextlib
import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import benchmark
from generator import make_random_puzzle
from search import ALGORITHMS, SearchAlgorithm, get_algorithm, greedy_best_first


class SearchRegistryTests(unittest.TestCase):
    def setUp(self):
        self.puzzle, _ = make_random_puzzle(3, 3, seed=42, sparse=True)

    def test_registered_greedy_preserves_solution_and_statistics(self):
        result = get_algorithm("greedy").solver(self.puzzle)
        expected = greedy_best_first(self.puzzle)
        self.assertTrue(result.found)
        self.assertEqual(result.path, expected.path)
        self.assertEqual(result.actions, expected.actions)
        self.assertEqual(result.nodes_generated, expected.nodes_generated)
        self.assertEqual(result.nodes_expanded, expected.nodes_expanded)

    def test_unavailable_algorithm_is_rejected_before_solver_runs(self):
        solver = Mock()
        pending = SearchAlgorithm("pending", "Pending", solver, available=False)
        with patch.dict(ALGORITHMS, {"pending": pending}):
            with self.assertRaises(NotImplementedError):
                get_algorithm("pending").solver(self.puzzle)
        solver.assert_not_called()

    def test_unknown_algorithm_has_a_clear_error(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            get_algorithm("missing")

    def test_benchmark_dispatches_selected_solver_and_labels_csv(self):
        solver = Mock(wraps=greedy_best_first)
        probe = SearchAlgorithm("probe", "Probe", solver)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.csv"
            with (patch.dict(ALGORITHMS, {"probe": probe}),
                  patch.object(benchmark, "PUZZLES", ["puzzles/tiny_3x3.json"]),
                  contextlib.redirect_stdout(io.StringIO())):
                benchmark.run("probe", max_nodes=1, output=str(output))
            rows = list(csv.DictReader(io.StringIO(output.read_text(encoding="utf-8"))))
        solver.assert_called_once()
        self.assertEqual(solver.call_args.kwargs["max_nodes"], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["puzzle"], "tiny_3x3")
        self.assertEqual(rows[0]["algorithm"], "Greedy Best-First")
        self.assertEqual(rows[0]["found"], "False")

    def test_benchmark_does_not_overwrite_output_for_unavailable_algorithm(self):
        pending = SearchAlgorithm("pending", "Pending", Mock(), available=False)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.csv"
            output.write_text("existing results", encoding="utf-8")
            with patch.dict(ALGORITHMS, {"pending": pending}):
                with self.assertRaises(NotImplementedError):
                    benchmark.run("pending", output=str(output))
            self.assertEqual(output.read_text(encoding="utf-8"), "existing results")


if __name__ == "__main__":
    unittest.main()
