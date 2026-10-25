import os
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from generator import make_random_puzzle
from main import App
from search import greedy_best_first


class TraceUITests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.app.puzzle, self.app.solution_state = make_random_puzzle(3, 3, seed=42, sparse=True)
        self.app.reset()

    def tearDown(self):
        self.app._invalidate_search()
        if self.app.search_worker is not None:
            self.app.search_worker.join(timeout=5)
        pygame.quit()

    def finish_worker(self):
        deadline = time.perf_counter() + 10
        while self.app.search_computing and time.perf_counter() < deadline:
            self.app.update()
            time.sleep(0.001)
        self.assertFalse(self.app.search_computing, "Search worker did not finish")

    def test_worker_opens_paused_and_navigation_matches_parent(self):
        app = self.app
        start = app.state
        app.run_greedy()
        self.finish_worker()
        self.assertTrue(app.search_result.found)
        self.assertFalse(app.search_running)
        self.assertTrue(app.search_paused)
        self.assertEqual(app.trace_index, 0)
        self.assertEqual(app.state, start)
        app.step_search()
        self.assertEqual(app.state, app.current_trace.state)
        self.assertEqual(app.previous_state, app.current_trace.parent_state)
        app.step_search(-1)
        self.assertEqual(app.state, start)
        app.toggle_pause()
        self.assertTrue(app.search_running)
        app.step_search()
        self.assertFalse(app.search_running)
        app.draw()
        app.seek_timeline(app.timeline_rect.right)
        self.assertTrue(app.current_trace.is_goal)
        app.toggle_pause()
        self.assertEqual(app.trace_index, 0)
        self.assertTrue(app.search_running)

    def test_solution_tab_clicks_seeking_and_replay(self):
        app = self.app
        app.run_greedy()
        self.finish_worker()
        app.draw()
        app.handle_click(app.inspector_buttons["solution"].center)
        self.assertEqual(app.view_mode, "solution")
        app.select_step(len(app.search_path) - 1)
        self.assertTrue(app.solved)
        app.draw()
        app.handle_click(app.solution_buttons[1].center)
        self.assertEqual(app.search_step, 1)
        self.assertEqual(app.previous_state, app.search_path[0])
        saved_delay = app.auto_delay
        app.handle_click(app.action_buttons["speed"].center)
        self.assertNotEqual(app.auto_delay, saved_delay)
        app.toggle_pause()
        app.last_step_time -= app.auto_delay + 1
        app.update()
        self.assertEqual(app.search_step, 2)
        app.set_view("trace")
        self.assertFalse(app.search_running)
        self.assertEqual(app.state, app.trace_steps[app.trace_index].state)

    def test_branch_switch_highlights_actual_parent_move(self):
        app = self.app
        app.puzzle, app.solution_state = make_random_puzzle(3, 3, seed=29, sparse=True)
        app.reset()
        app.run_greedy()
        self.finish_worker()
        branch = next(i for i in range(1, len(app.trace_steps)) if app.trace_steps[i].parent_state != app.trace_steps[i - 1].state)
        app.select_step(branch - 1)
        last_expanded_state = app.state
        app.step_search()
        self.assertNotEqual(app.previous_state, last_expanded_state)
        self.assertEqual(app.previous_state, app.current_trace.parent_state)
        self.assertEqual(sum(a != b for a, b in zip(app.previous_state, app.state)), 1)
        app.draw()

    def test_reset_discards_stale_worker_records_and_restores_manual_play(self):
        app = self.app
        steps = []
        greedy_best_first(app.puzzle, trace_callback=steps.append)
        token = app.search_token
        app.reset()
        for step in steps:
            app.pending_traces.put((token, step))
        app.update()
        self.assertEqual(app.trace_steps, [])
        self.assertIsNone(app.search_result)
        self.assertEqual(app.state, app.puzzle.initial_state())
        index = next(i for i, cell in enumerate(app.puzzle.cells) if not cell.locked and cell.type not in ("CROSS", "EMPTY"))
        row, col = app.puzzle.rc(index)
        old_rotation = app.state[index]
        app.on_board_click((app.grid_left + col * app.cell_size + 10, app.grid_top + row * app.cell_size + 10))
        self.assertEqual(app.state[index], (old_rotation + 1) % 4)

    def test_solved_start_and_all_grid_sizes_draw(self):
        app = self.app
        app.state = app.solution_state
        app.run_greedy()
        self.finish_worker()
        self.assertEqual(len(app.trace_steps), 1)
        app.draw()
        app.toggle_pause()
        app.update()
        app.set_view("solution")
        app.draw()
        for key in ("1", "2", "3", "4"):
            app.switch_puzzle(key)
            app.draw()
            self.assertLess(app.grid_top + app.board_size, app.board_top + 605)
            self.assertGreaterEqual(app.grid_top - 20, app.board_top + 72 + app.font_tiny.get_linesize())


if __name__ == "__main__":
    unittest.main()
