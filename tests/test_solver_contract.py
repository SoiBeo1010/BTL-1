"""Shared behavioral contract for both search strategies."""
import inspect
import tracemalloc
import unittest

from puzzle import Cell, PipesPuzzle
from search import depth_first_search, greedy_best_first, validate_solution
from search.common import SearchSolver
from tests.helpers import Graph

SOLVERS = (depth_first_search, greedy_best_first)


class SolverContractTests(unittest.TestCase):
    def test_solver_signatures_match_the_public_protocol(self):
        expected = list(inspect.signature(SearchSolver.__call__).parameters.values())[1:]
        for solver in SOLVERS:
            with self.subTest(solver=solver.__name__):
                actual = list(inspect.signature(solver).parameters.values())
                self.assertEqual([(p.name, p.kind, p.default) for p in actual],
                                 [(p.name, p.kind, p.default) for p in expected])

    def test_each_solver_returns_a_legal_pipes_solution(self):
        puzzle = PipesPuzzle(1, 2, [Cell("END", 1, True), Cell("END", 1)], root_index=0)
        original = puzzle.to_dict()
        for solver in SOLVERS:
            with self.subTest(solver=solver.__name__):
                result = solver(puzzle)
                self.assertTrue(validate_solution(puzzle, result))
                self.assertEqual(result.termination_reason, "solved")
                self.assertEqual(puzzle.to_dict(), original)

    def test_explicit_start_and_solved_start(self):
        for solver in SOLVERS:
            with self.subTest(solver=solver.__name__):
                result = solver(Graph(), start_state=(2,))
                self.assertEqual(result.path[0], (2,))
                self.assertTrue(validate_solution(Graph(), result, start=(2,)))
                steps = []
                solved = solver(Graph(), start_state=(4,), trace_callback=steps.append)
                self.assertEqual((solved.depth, solved.nodes_generated, solved.nodes_expanded), (0, 1, 0))
                self.assertEqual(solved.path, [(4,)])
                self.assertEqual(steps[0].number, 0)
                self.assertTrue(steps[0].is_goal)

    def test_legacy_positional_callback_still_works(self):
        for solver in SOLVERS:
            with self.subTest(solver=solver.__name__):
                expanded = []
                result = solver(Graph(), 100, lambda state, *_: expanded.append(state))
                self.assertEqual(len(expanded), result.nodes_expanded)

    def test_node_budget_and_exhaustion(self):
        for solver in SOLVERS:
            for limit in (0, 1, 2):
                with self.subTest(solver=solver.__name__, limit=limit):
                    result = solver(Graph(), max_nodes=limit)
                    self.assertEqual(result.termination_reason, "node_limit")
                    self.assertEqual(result.nodes_generated, limit + 1)
                    self.assertEqual((result.path, result.actions, result.depth), ([], [], -1))
            exhausted = solver(Graph(goal=99))
            self.assertEqual(exhausted.termination_reason, "exhausted")
            self.assertEqual(exhausted.nodes_expanded, 5)

    def test_cancellation_is_latched_even_if_check_is_only_true_once(self):
        for solver in SOLVERS:
            with self.subTest(solver=solver.__name__):
                cancelled = solver(Graph(), cancel_check=lambda: True)
                self.assertEqual(cancelled.termination_reason, "cancelled")
                self.assertEqual(cancelled.nodes_expanded, 0)
                calls = 0

                def cancel():
                    nonlocal calls
                    calls += 1
                    return calls == 3

                result = solver(Graph(), cancel_check=cancel)
                self.assertEqual(result.termination_reason, "cancelled")
                self.assertEqual(result.nodes_generated, 2)

    def test_depth_limit_and_goal_exactly_at_the_limit(self):
        graph = Graph(goal=2, edges={0: [1], 1: [2]})
        for solver in SOLVERS:
            with self.subTest(solver=solver.__name__):
                trace = []
                stopped = solver(graph, max_depth=1, trace_callback=trace.append)
                self.assertFalse(stopped.found)
                self.assertEqual(stopped.termination_reason, "depth_limit")
                self.assertTrue(trace[-1].depth_limited)
                self.assertFalse(trace[-1].is_goal)
                self.assertFalse(trace[-1].candidates)
                trace = []
                solved = solver(graph, max_depth=2, trace_callback=trace.append)
                self.assertEqual(solved.depth, 2)
                self.assertTrue(validate_solution(graph, solved))
                self.assertTrue(trace[-1].is_goal)
                self.assertFalse(trace[-1].depth_limited)
                self.assertEqual(solver(graph, max_depth=0).nodes_generated, 1)

    def test_max_depth_reached_is_measured_even_when_solution_is_shallower(self):
        graph = Graph(goal=2, edges={0: [1, 2], 1: [3], 3: [4], 4: []},
                      heuristics={0: 0, 1: 0, 3: 0, 4: 0, 2: 100})
        for solver in SOLVERS:
            with self.subTest(solver=solver.__name__):
                trace = []
                result = solver(graph, trace_callback=trace.append, max_depth=None)
                self.assertTrue(result.found)
                self.assertEqual(result.depth, 1)
                self.assertEqual(result.max_depth_reached, 3)
                self.assertEqual(result.max_depth_reached, max(step.depth for step in trace))
                self.assertEqual(solver(graph, start_state=(2,)).max_depth_reached, 0)

    def test_shorter_path_reopens_depth_limited_state_without_rewriting_trace_parents(self):
        graph = Graph(goal=5, edges={0: [1, 2], 1: [3], 3: [4], 2: [4], 4: [5]},
                      heuristics={0: 9, 1: 0, 2: 10, 3: 0, 4: 0, 5: 0})
        for solver in SOLVERS:
            with self.subTest(solver=solver.__name__):
                trace = []
                result = solver(graph, max_depth=3, trace_callback=trace.append)
                self.assertTrue(validate_solution(graph, result))
                self.assertEqual(result.path, [(0,), (2,), (4,), (5,)])
                visits = [step for step in trace if step.state == (4,)]
                self.assertEqual([step.depth for step in visits], [3, 2])
                self.assertEqual([step.parent_state for step in visits], [(3,), (2,)])
                self.assertNotEqual(visits[0].node_id, visits[1].node_id)
                by_id = {step.node_id: step for step in trace}
                for step in trace:
                    if step.parent_id is not None:
                        self.assertEqual(by_id[step.parent_id].state, step.parent_state)
                        self.assertEqual(by_id[step.parent_id].depth + 1, step.depth)

    def test_trace_limit_keeps_the_goal_and_actual_heuristic(self):
        for solver in SOLVERS:
            for limit in (0, 1):
                with self.subTest(solver=solver.__name__, limit=limit):
                    plain = solver(Graph())
                    trace = []
                    traced = solver(Graph(), trace_callback=trace.append, trace_limit=limit)
                    self.assertEqual(len(trace), limit + 1)
                    self.assertTrue(trace[-1].is_goal)
                    self.assertEqual(trace[-1].heuristic, Graph().heuristic(trace[-1].state))
                    for field in ("path", "actions", "depth", "nodes_generated", "nodes_expanded", "max_frontier"):
                        self.assertEqual(getattr(traced, field), getattr(plain, field))

    def test_frontier_preview_skips_entries_replaced_by_a_shorter_path(self):
        graph = Graph(goal=5, edges={0: [1, 2], 1: [3], 3: [4], 2: [4], 4: [5]},
                      heuristics={0: 0, 1: 0, 2: 100, 3: 0, 4: 1000, 5: 2000})
        trace = []
        result = greedy_best_first(graph, max_depth=4, trace_callback=trace.append)
        self.assertTrue(validate_solution(graph, result))
        for step, following in zip(trace, trace[1:]):
            self.assertEqual(step.frontier_preview[0].node_id, following.node_id)

    def test_callback_exception_releases_owned_memory_tracer(self):
        def fail(*args):
            raise RuntimeError("callback failed")

        for solver in SOLVERS:
            with self.subTest(solver=solver.__name__):
                self.assertFalse(tracemalloc.is_tracing())
                with self.assertRaisesRegex(RuntimeError, "callback failed"):
                    solver(Graph(), callback=fail)
                self.assertFalse(tracemalloc.is_tracing())

    def test_existing_memory_tracer_is_preserved_on_success_and_error(self):
        def fail(*args):
            raise RuntimeError("callback failed")

        tracemalloc.start()
        try:
            for solver in SOLVERS:
                with self.subTest(solver=solver.__name__):
                    self.assertTrue(solver(Graph()).found)
                    self.assertTrue(tracemalloc.is_tracing())
                    with self.assertRaises(RuntimeError):
                        solver(Graph(), callback=fail)
                    self.assertTrue(tracemalloc.is_tracing())
        finally:
            tracemalloc.stop()

    def test_invalid_limits_are_rejected(self):
        for solver in SOLVERS:
            for kwargs in ({"max_nodes": -1}, {"max_depth": -1}, {"max_depth": 1.5}, {"trace_limit": -1}):
                with self.subTest(solver=solver.__name__, kwargs=kwargs):
                    with self.assertRaises(ValueError):
                        solver(Graph(), **kwargs)

    def test_solution_validation_rejects_actions_outside_successors(self):
        result = depth_first_search(Graph())
        result.actions[0] = "not a legal action"
        self.assertFalse(validate_solution(Graph(), result))
