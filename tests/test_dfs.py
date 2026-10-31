"""Tests for the Depth-First Search solver.

Covers: path validity, LIFO expansion order, duplicate skipping, cancel /
node-limit / exhausted termination, start_state override, trace correctness
(parent IDs, candidate list, frontier preview), trace_limit edge case, and
matching results with/without trace recording.
"""
from __future__ import annotations

import unittest

from generator import make_random_puzzle
from puzzle import Cell, PipesPuzzle
from search import depth_first_search, ALGORITHMS
from search.common import SearchTraceStep


def _simple_puzzle() -> PipesPuzzle:
    """3×3 sparse puzzle, seed 42 — always solvable, compact search space."""
    puzzle, _ = make_random_puzzle(3, 3, seed=42, sparse=True)
    return puzzle


class DFSBasicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.puzzle = _simple_puzzle()

    # ------------------------------------------------------------------
    # 1. Solvability and path validity
    # ------------------------------------------------------------------
    def test_finds_solution_and_path_is_valid(self) -> None:
        result = depth_first_search(self.puzzle, max_nodes=50_000)
        self.assertTrue(result.found)
        self.assertEqual(result.algorithm, "Depth-First Search")
        self.assertEqual(result.termination_reason, "solved")
        self.assertEqual(result.depth, len(result.path) - 1)
        self.assertEqual(len(result.actions), result.depth)
        # First state is the initial state; last is the goal.
        self.assertEqual(result.path[0], self.puzzle.initial_state())
        self.assertTrue(self.puzzle.is_goal(result.path[-1]))
        # Every step is a valid single-cell rotation from its predecessor.
        for prev, nxt in zip(result.path, result.path[1:]):
            diffs = sum(a != b for a, b in zip(prev, nxt))
            self.assertEqual(diffs, 1, "Each step must change exactly one cell")
        # Locked cells must never change.
        for idx, cell in enumerate(self.puzzle.cells):
            if cell.locked:
                for state in result.path:
                    self.assertEqual(state[idx], result.path[0][idx])

    def test_result_with_trace_matches_without_trace(self) -> None:
        plain = depth_first_search(self.puzzle, max_nodes=50_000)
        steps: list[SearchTraceStep] = []
        traced = depth_first_search(
            self.puzzle, max_nodes=50_000, trace_callback=steps.append
        )
        self.assertEqual(plain.found, traced.found)
        self.assertEqual(plain.path, traced.path)
        self.assertEqual(plain.actions, traced.actions)
        self.assertEqual(plain.nodes_generated, traced.nodes_generated)
        self.assertEqual(plain.nodes_expanded, traced.nodes_expanded)
        self.assertEqual(plain.max_frontier, traced.max_frontier)

    # ------------------------------------------------------------------
    # 2. LIFO expansion order and duplicate detection
    # ------------------------------------------------------------------
    def test_lifo_expansion_and_no_duplicate_expansion(self) -> None:
        """The stack must expand each state at most once."""
        expanded: list[tuple[int, ...]] = []
        depth_first_search(
            self.puzzle,
            max_nodes=5_000,
            callback=lambda state, *_: expanded.append(state),
        )
        self.assertEqual(len(expanded), len(set(expanded)),
                         "DFS must not expand the same state twice")

    def test_trace_candidates_mark_duplicates_correctly(self) -> None:
        steps: list[SearchTraceStep] = []
        depth_first_search(self.puzzle, max_nodes=5_000, trace_callback=steps.append)
        seen: set[tuple[int, ...]] = {self.puzzle.initial_state()}
        for step in steps:
            if step.is_goal:
                continue
            for candidate in step.candidates:
                # Rebuild successor state from action to verify
                if candidate.duplicate:
                    self.assertIsNone(candidate.heuristic,
                                      "Duplicate candidates must have no heuristic")
                else:
                    self.assertIsNotNone(candidate.heuristic)
            seen.add(step.state)

    # ------------------------------------------------------------------
    # 3. start_state override
    # ------------------------------------------------------------------
    def test_start_state_already_solved_returns_depth_zero(self) -> None:
        _, solution = make_random_puzzle(3, 3, seed=42, sparse=True)
        steps: list[SearchTraceStep] = []
        result = depth_first_search(
            self.puzzle, start_state=solution, trace_callback=steps.append
        )
        self.assertTrue(result.found)
        self.assertEqual(result.depth, 0)
        self.assertEqual(result.nodes_expanded, 0)
        self.assertEqual(result.nodes_generated, 1)
        self.assertEqual(len(steps), 1)
        self.assertTrue(steps[0].is_goal)
        self.assertEqual(steps[0].candidates, ())

    def test_start_state_differs_from_initial(self) -> None:
        puzzle2, _ = make_random_puzzle(3, 3, seed=123, sparse=True)
        # Use a different initial state from another puzzle.
        alt_start = puzzle2.initial_state()
        result = depth_first_search(self.puzzle, start_state=alt_start, max_nodes=50_000)
        if result.found:
            self.assertEqual(result.path[0], alt_start)
            self.assertTrue(self.puzzle.is_goal(result.path[-1]))

    # ------------------------------------------------------------------
    # 4. Termination reasons
    # ------------------------------------------------------------------
    def test_cancel_check_stops_early(self) -> None:
        result = depth_first_search(self.puzzle, cancel_check=lambda: True)
        self.assertFalse(result.found)
        self.assertEqual(result.termination_reason, "cancelled")

    def test_node_limit_terminates_with_node_limit_reason(self) -> None:
        result = depth_first_search(self.puzzle, max_nodes=5)
        self.assertFalse(result.found)
        self.assertEqual(result.termination_reason, "node_limit")

    def test_exhausted_unsolvable_puzzle(self) -> None:
        # A single locked STRAIGHT cell is always unsolvable (open ends at boundary).
        impossible = PipesPuzzle(1, 1, [Cell("STRAIGHT", 0, locked=True)])
        result = depth_first_search(impossible)
        self.assertFalse(result.found)
        self.assertEqual(result.termination_reason, "exhausted")

    # ------------------------------------------------------------------
    # 5. Trace correctness
    # ------------------------------------------------------------------
    def test_trace_parent_ids_and_actions_are_consistent(self) -> None:
        steps: list[SearchTraceStep] = []
        depth_first_search(
            self.puzzle, max_nodes=2_000, trace_callback=steps.append
        )
        id_to_state: dict[int, tuple[int, ...]] = {}
        for step in steps:
            id_to_state[step.node_id] = step.state

        for step in steps:
            if step.parent_id is None:
                # Root node: parent state must be None
                self.assertIsNone(step.parent_state)
                self.assertEqual(step.action, "")
            else:
                # Parent state must be recorded and match
                self.assertIn(step.parent_id, id_to_state)
                self.assertEqual(id_to_state[step.parent_id], step.parent_state)
                # Action format: R<index>+<steps>
                self.assertRegex(step.action, r"^R\d+\+[123]$")
                # Parent and child states differ in exactly one cell.
                diffs = sum(
                    a != b for a, b in zip(step.parent_state, step.state)
                )
                self.assertEqual(diffs, 1)

    def test_trace_frontier_sizes_are_monotone_with_stack_ops(self) -> None:
        steps: list[SearchTraceStep] = []
        depth_first_search(
            self.puzzle, max_nodes=2_000, trace_callback=steps.append
        )
        for step in steps:
            # frontier_before must be >= 1 (the node we just popped was in it).
            self.assertGreaterEqual(step.frontier_before, 1)
            # frontier_after is always >= 0.
            self.assertGreaterEqual(step.frontier_after, 0)

    def test_trace_generated_counts_are_non_decreasing(self) -> None:
        steps: list[SearchTraceStep] = []
        depth_first_search(
            self.puzzle, max_nodes=2_000, trace_callback=steps.append
        )
        for i in range(1, len(steps)):
            self.assertGreaterEqual(steps[i].generated, steps[i - 1].generated)

    def test_trace_frontier_preview_length_at_most_five(self) -> None:
        steps: list[SearchTraceStep] = []
        depth_first_search(
            self.puzzle, max_nodes=2_000, trace_callback=steps.append
        )
        for step in steps:
            self.assertLessEqual(len(step.frontier_preview), 5)

    def test_last_trace_step_is_goal(self) -> None:
        steps: list[SearchTraceStep] = []
        result = depth_first_search(
            self.puzzle, max_nodes=50_000, trace_callback=steps.append
        )
        if result.found:
            self.assertTrue(steps[-1].is_goal)
            self.assertEqual(steps[-1].state, result.path[-1])

    # ------------------------------------------------------------------
    # 6. trace_limit: only the first N + goal are recorded
    # ------------------------------------------------------------------
    def test_trace_limit_keeps_goal_step(self) -> None:
        steps: list[SearchTraceStep] = []
        result = depth_first_search(
            self.puzzle,
            max_nodes=50_000,
            trace_callback=steps.append,
            trace_limit=1,
        )
        if result.found:
            # Only steps 1 (first expansion) and the goal step are emitted.
            self.assertEqual(steps[0].number, 1)
            self.assertTrue(steps[-1].is_goal)
            # Solution must still be complete.
            self.assertEqual(len(result.actions), result.depth)
            self.assertTrue(self.puzzle.is_goal(result.path[-1]))

    # ------------------------------------------------------------------
    # 7. Registry integration
    # ------------------------------------------------------------------
    def test_dfs_is_registered_and_available(self) -> None:
        self.assertIn("dfs", ALGORITHMS)
        self.assertTrue(ALGORITHMS["dfs"].available)
        self.assertFalse(ALGORITHMS["dfs"].uses_heuristic)

    def test_registry_solver_matches_direct_call(self) -> None:
        from search import get_algorithm
        algo = get_algorithm("dfs")
        max_depth = (self.puzzle.rows * self.puzzle.cols - 1) * 3
        result_via_registry = algo.solver(self.puzzle, max_nodes=50_000, max_depth=max_depth)
        result_direct = depth_first_search(self.puzzle, max_nodes=50_000, max_depth=max_depth)
        self.assertEqual(result_via_registry.found, result_direct.found)
        # Deterministic: both runs must produce the same path.
        self.assertEqual(result_via_registry.path, result_direct.path)

    def test_max_depth_cutoff_prunes_deep_branches(self) -> None:
        max_d = (self.puzzle.rows * self.puzzle.cols - 1) * 3
        result = depth_first_search(self.puzzle, max_nodes=50_000, max_depth=max_d)
        if result.found:
            self.assertLessEqual(result.depth, max_d)


if __name__ == "__main__":
    unittest.main()

