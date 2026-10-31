"""Small deterministic graphs for checking search behavior without large puzzles."""


class Graph:
    def __init__(self, goal=4, edges=None, heuristics=None):
        self.goal = goal
        self.edges = edges if edges is not None else {
            0: [1, 2], 1: [0, 3], 2: [0, 3, 4], 3: [1], 4: [2],
        }
        self.heuristics = heuristics or {}

    def initial_state(self):
        return (0,)

    def is_goal(self, state):
        return state == (self.goal,)

    def successors(self, state):
        for target in self.edges.get(state[0], []):
            yield (target,), f"{state[0]}->{target}"

    def heuristic(self, state):
        return self.heuristics.get(state[0], -state[0])
