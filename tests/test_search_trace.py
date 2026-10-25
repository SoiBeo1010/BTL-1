import heapq
import unittest

from generator import make_random_puzzle
from puzzle import Cell, PipesPuzzle
from search import greedy_best_first


class SearchTraceTests(unittest.TestCase):
    def setUp(self):
        self.puzzle, self.solution = make_random_puzzle(3, 3, seed=42, sparse=True)

    def test_trace_replays_real_frontier_and_duplicate_decisions(self):
        self.puzzle, _ = make_random_puzzle(3, 3, seed=29, sparse=True)
        steps = []
        result = greedy_best_first(self.puzzle, trace_callback=steps.append)
        plain = greedy_best_first(self.puzzle)
        self.assertTrue(result.found)
        self.assertEqual(result.path, plain.path)
        self.assertEqual(result.actions, plain.actions)
        self.assertEqual(result.nodes_generated, plain.nodes_generated)
        self.assertEqual(result.nodes_expanded, len(steps))
        self.assertEqual(result.max_frontier, plain.max_frontier)
        self.assertTrue(any(steps[i].parent_state != steps[i - 1].state for i in range(1, len(steps))))

        start = self.puzzle.initial_state()
        frontier = [(self.puzzle.heuristic(start), 0, 0, start)]
        visited = {start: 0}
        parents = {start: (None, None, "")}
        max_frontier = 1
        for step in steps:
            self.assertEqual(step.frontier_before, len(frontier))
            h, depth, node_id, state = heapq.heappop(frontier)
            self.assertEqual((step.heuristic, step.depth, step.node_id, step.state), (h, depth, node_id, state))
            self.assertEqual((step.parent_state, step.parent_id, step.action), parents[state])
            self.assertEqual(step.is_goal, self.puzzle.is_goal(state))
            successors = [] if step.is_goal else list(self.puzzle.successors(state))
            self.assertEqual(len(step.candidates), len(successors))
            for candidate, (successor, action) in zip(step.candidates, successors):
                self.assertEqual(candidate.action, action)
                self.assertEqual(candidate.duplicate, successor in visited)
                if candidate.duplicate:
                    self.assertIsNone(candidate.heuristic)
                    self.assertEqual(candidate.node_id, visited[successor])
                else:
                    self.assertEqual(candidate.heuristic, self.puzzle.heuristic(successor))
                    self.assertEqual(candidate.node_id, len(visited))
                    visited[successor] = candidate.node_id
                    parents[successor] = (state, node_id, action)
                    heapq.heappush(frontier, (candidate.heuristic, depth + 1, candidate.node_id, successor))
            max_frontier = max(max_frontier, len(frontier))
            self.assertEqual(step.frontier_after, len(frontier))
            self.assertEqual(step.max_frontier, max_frontier)
            self.assertEqual(step.generated, len(visited))
            expected = heapq.nsmallest(5, frontier)
            self.assertEqual([(item.heuristic, item.depth, item.node_id) for item in step.frontier_preview], [item[:3] for item in expected])
        self.assertTrue(steps[-1].is_goal)
        self.assertEqual(steps[-1].state, result.path[-1])

    def test_recording_limit_keeps_goal_and_complete_solution(self):
        steps = []
        result = greedy_best_first(self.puzzle, trace_callback=steps.append, trace_limit=1)
        self.assertTrue(result.found)
        self.assertEqual([step.number for step in steps], [1, result.nodes_expanded])
        self.assertTrue(steps[-1].is_goal)
        self.assertEqual(len(result.actions), result.depth)
        self.assertTrue(self.puzzle.is_goal(result.path[-1]))

    def test_solved_start_emits_goal_without_rotations(self):
        steps = []
        result = greedy_best_first(self.puzzle, start_state=self.solution, trace_callback=steps.append)
        self.assertTrue(result.found)
        self.assertEqual(result.depth, 0)
        self.assertEqual(result.nodes_expanded, 0)
        self.assertEqual(len(steps), 1)
        self.assertTrue(steps[0].is_goal)
        self.assertEqual(steps[0].candidates, ())

    def test_stopping_reasons_do_not_claim_unsolvability(self):
        result = greedy_best_first(self.puzzle, cancel_check=lambda: True)
        self.assertFalse(result.found)
        self.assertEqual(result.termination_reason, "cancelled")
        result = greedy_best_first(self.puzzle, max_nodes=1)
        self.assertFalse(result.found)
        self.assertEqual(result.termination_reason, "node_limit")
        # Two outward openings ensure a nonzero mismatch score on this board.
        impossible = PipesPuzzle(1, 1, [Cell("STRAIGHT", 0, locked=True)])
        result = greedy_best_first(impossible)
        self.assertFalse(result.found)
        self.assertEqual(result.termination_reason, "exhausted")


if __name__ == "__main__":
    unittest.main()
