import tracemalloc
import unittest

from puzzle import Cell, PipesPuzzle
from search import depth_first_search, get_algorithm


class Graph:
    # A cycle, converging edges, and siblings whose heuristic opposes LIFO.
    edges = {0: [1, 2], 1: [0, 3], 2: [0, 3, 4], 3: [1], 4: [2]}

    def __init__(self, goal=1):
        self.goal = goal

    def initial_state(self):
        return (0,)

    def is_goal(self, state):
        return state == (self.goal,)

    def successors(self, state):
        for target in self.edges.get(state[0], []):
            yield (target,), f'{state[0]}->{target}'

    def heuristic(self, state):
        return state[0] * 100


class DFSTests(unittest.TestCase):
    def test_lifo_cycles_and_real_trace_parents(self):
        graph = Graph()
        steps, expanded, progress = [], [], []
        result = depth_first_search(graph, trace_callback=steps.append,
                                    callback=lambda *args: expanded.append(args),
                                    progress_callback=lambda *args: progress.append(args))
        self.assertEqual([s.state for s in steps], [(0,), (2,), (4,), (3,), (1,)])
        self.assertEqual(result.path, [(0,), (1,)])
        self.assertEqual(result.actions, ['0->1'])
        self.assertEqual(result.nodes_generated, 5)
        self.assertEqual(result.nodes_expanded, 5)
        self.assertEqual(result.max_frontier, 3)
        self.assertEqual([x[0] for x in expanded], [s.state for s in steps])
        self.assertTrue(progress)
        stack, ids, parents = [(0,)], {(0,): 0}, {(0,): (None, '')}
        max_frontier = 1
        for number, step in enumerate(steps, 1):
            self.assertEqual(step.number, number)
            self.assertEqual(step.frontier_before, len(stack))
            self.assertEqual(step.state, stack.pop())
            self.assertEqual(step.node_id, ids[step.state])
            parent, action = parents[step.state]
            self.assertEqual((step.parent_state, step.action), (parent, action))
            self.assertEqual(step.parent_id, ids[parent] if parent is not None else None)
            depth, ancestor = 0, parent
            while ancestor is not None:
                depth += 1
                ancestor = parents[ancestor][0]
            self.assertEqual(step.depth, depth)
            children = [] if step.is_goal else list(graph.successors(step.state))
            self.assertEqual(len(children), len(step.candidates))
            for (child, action), candidate in zip(children, step.candidates):
                self.assertEqual(candidate.action, action)
                self.assertEqual(candidate.duplicate, child in ids)
                if child in ids:
                    self.assertIsNone(candidate.heuristic)
                else:
                    ids[child] = len(ids)
                    parents[child] = (step.state, action)
                    stack.append(child)
                    self.assertEqual(candidate.heuristic, graph.heuristic(child))
                self.assertEqual(candidate.node_id, ids[child])
            max_frontier = max(max_frontier, len(stack))
            self.assertEqual(step.generated, len(ids))
            self.assertEqual(step.max_frontier, max_frontier)
            self.assertEqual(step.frontier_after, len(stack))
            self.assertEqual([p.node_id for p in step.frontier_preview],
                             [ids[s] for s in reversed(stack[-5:])])

    def test_small_pipes_solution_preserves_actions_and_locked_cells(self):
        # Only the last of two end caps needs a half-turn.
        puzzle = PipesPuzzle(1, 2, [Cell('END', 1, True), Cell('END', 1)], root_index=0)
        original = puzzle.to_dict()
        result = get_algorithm('dfs').solver(puzzle)
        self.assertTrue(result.found)
        self.assertEqual(result.algorithm, 'Depth-First Search')
        self.assertEqual(result.termination_reason, 'solved')
        self.assertEqual(result.depth, len(result.actions))
        self.assertEqual(result.depth, len(result.path)-1)
        for state, next_state, action in zip(result.path, result.path[1:], result.actions):
            self.assertIn((next_state, action), list(puzzle.successors(state)))
            self.assertEqual(next_state[0], 1)
        self.assertTrue(puzzle.is_goal(result.path[-1]))
        self.assertEqual(puzzle.to_dict(), original)
        self.assertGreaterEqual(result.peak_memory_kb, 0)

    def test_trace_limit_keeps_goal_without_changing_search(self):
        plain = depth_first_search(Graph())
        for limit in (0, 1):
            steps = []
            traced = depth_first_search(Graph(), trace_callback=steps.append, trace_limit=limit)
            self.assertEqual(len(steps), limit+1)
            self.assertTrue(steps[-1].is_goal)
            self.assertEqual(steps[-1].number, plain.nodes_expanded)
            for field in ('path', 'actions', 'depth', 'nodes_generated', 'nodes_expanded', 'max_frontier'):
                self.assertEqual(getattr(traced, field), getattr(plain, field))

    def test_explicit_start_and_solved_start(self):
        result = depth_first_search(Graph(), start_state=(3,))
        self.assertEqual(result.path, [(3,), (1,)])
        steps = []
        solved = depth_first_search(Graph(), start_state=(1,), trace_callback=steps.append)
        self.assertEqual((solved.depth, solved.nodes_generated, solved.nodes_expanded), (0, 1, 0))
        self.assertEqual(solved.path, [(1,)])
        self.assertEqual(steps[0].number, 0)
        self.assertTrue(steps[0].is_goal)

    def test_cancel_before_and_during_generation(self):
        result = depth_first_search(Graph(), cancel_check=lambda: True)
        self.assertEqual(result.termination_reason, 'cancelled')
        self.assertEqual(result.nodes_expanded, 0)
        calls = 0
        def cancel():
            nonlocal calls
            calls += 1
            return calls == 3
        result = depth_first_search(Graph(), cancel_check=cancel)
        self.assertEqual(result.termination_reason, 'cancelled')
        self.assertEqual(result.nodes_generated, 2)

    def test_limits_and_exhaustion(self):
        for limit in (0, 1, 2):
            result = depth_first_search(Graph(), max_nodes=limit)
            self.assertEqual(result.termination_reason, 'node_limit')
            self.assertEqual(result.nodes_generated, limit+1)
            self.assertFalse(result.found)
            self.assertEqual((result.path, result.actions, result.depth), ([], [], -1))
        result = depth_first_search(Graph(goal=99))
        self.assertEqual(result.termination_reason, 'exhausted')
        self.assertEqual(result.nodes_expanded, 5)

    def test_plain_dfs_never_consults_heuristic(self):
        graph = Graph()
        def fail(state):
            raise AssertionError('Heuristic must not guide DFS')
        graph.heuristic = fail
        self.assertTrue(depth_first_search(graph).found)

    def test_callback_exception_releases_memory_tracer(self):
        def fail(*args):
            raise RuntimeError('callback failed')
        with self.assertRaises(RuntimeError):
            depth_first_search(Graph(), callback=fail)
        self.assertFalse(tracemalloc.is_tracing())


if __name__ == '__main__':
    unittest.main()
