"""DFS-specific traversal and trace checks; shared behavior is tested separately."""
import unittest

from search import ALGORITHMS, depth_first_search, get_algorithm
from tests.helpers import Graph


class DFSTests(unittest.TestCase):
    def test_lifo_order_cycles_duplicates_and_real_trace_parents(self):
        graph = Graph()
        steps, expanded, progress = [], [], []
        result = depth_first_search(
            graph, trace_callback=steps.append,
            callback=lambda *args: expanded.append(args),
            progress_callback=lambda *args: progress.append(args),
        )
        self.assertEqual([s.state for s in steps], [(0,), (1,), (3,), (2,), (4,)])
        self.assertEqual(result.path, [(0,), (2,), (4,)])
        self.assertEqual(result.actions, ["0->2", "2->4"])
        self.assertEqual(result.nodes_generated, 5)
        self.assertEqual(result.nodes_expanded, 5)
        self.assertEqual([x[0] for x in expanded], [s.state for s in steps])
        self.assertTrue(progress)
        stack, ids, parents = [(0,)], {(0,): 0}, {(0,): (None, "")}
        max_frontier = 1
        for number, step in enumerate(steps, 1):
            self.assertEqual(step.number, number)
            self.assertEqual(step.frontier_before, len(stack))
            self.assertEqual(step.state, stack.pop())
            self.assertEqual(step.node_id, ids[step.state])
            parent, action = parents[step.state]
            self.assertEqual((step.parent_state, step.action), (parent, action))
            self.assertEqual(step.parent_id, ids[parent] if parent is not None else None)
            children = [] if step.is_goal else list(graph.successors(step.state))
            self.assertEqual(len(children), len(step.candidates))
            pending = []
            for (child, action), candidate in zip(children, step.candidates):
                self.assertEqual(candidate.action, action)
                self.assertEqual(candidate.duplicate, child in ids)
                if child in ids:
                    self.assertIsNone(candidate.heuristic)
                else:
                    ids[child] = len(ids)
                    parents[child] = (step.state, action)
                    pending.append(child)
                    self.assertEqual(candidate.heuristic, graph.heuristic(child))
                self.assertEqual(candidate.node_id, ids[child])
            stack.extend(reversed(pending))
            max_frontier = max(max_frontier, len(stack))
            self.assertEqual(step.generated, len(ids))
            self.assertEqual(step.max_frontier, max_frontier)
            self.assertEqual(step.frontier_after, len(stack))
            self.assertEqual([p.node_id for p in step.frontier_preview],
                             [ids[s] for s in reversed(stack[-5:])])
            for entry in step.frontier_preview:
                state = next(state for state, ident in ids.items() if ident == entry.node_id)
                self.assertEqual(entry.heuristic, graph.heuristic(state))

    def test_plain_dfs_never_consults_heuristic(self):
        graph = Graph()

        def fail(state):
            raise AssertionError("Heuristic must not guide DFS")

        graph.heuristic = fail
        self.assertTrue(depth_first_search(graph).found)
        self.assertTrue(depth_first_search(graph, start_state=(4,)).found)

    def test_dfs_is_registered_and_registry_preserves_traversal(self):
        algorithm = get_algorithm("dfs")
        self.assertTrue(ALGORITHMS["dfs"].available)
        self.assertFalse(algorithm.uses_heuristic)
        self.assertIs(algorithm.solver, depth_first_search)
        expected = depth_first_search(Graph(), max_depth=4)
        self.assertEqual(algorithm.solver(Graph(), max_depth=4).path, expected.path)


if __name__ == "__main__":
    unittest.main()

