import os
from dataclasses import replace
import time
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from generator import make_random_puzzle
from config import default_max_depth
from main import App, BOARD_MARGIN, BOARD_W, CARD_H, GRID_AREA_BOTTOM, PUZZLE_SIZES
from search import ALGORITHMS, SearchAlgorithm, SearchResult, depth_first_search, greedy_best_first


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
        for key in PUZZLE_SIZES:
            app.switch_puzzle(key)
            app.draw()
            self.assertLessEqual(app.grid_top + app.board_size, app.board_top + CARD_H - GRID_AREA_BOTTOM)
            self.assertGreaterEqual(app.grid_top - 20, app.board_top + 72 + app.font_tiny.get_linesize())
            self.assertGreaterEqual(app.grid_left, BOARD_MARGIN)
            self.assertLessEqual(app.grid_left + app.board_size, BOARD_MARGIN + BOARD_W)

    def test_large_grid_can_be_selected_and_clicked_in_both_modes(self):
        app = self.app
        for sparse in (False, True):
            app.sparse_mode = sparse
            app.draw()
            app.handle_click(app.puzzle_buttons["5"].center)
            self.assertEqual((app.puzzle.rows, app.puzzle.cols), (7, 7))
            self.assertTrue(app.puzzle.is_goal(app.solution_state))
            app.draw()
            index = next(i for i in reversed(range(len(app.puzzle.cells)))
                         if not app.puzzle.cells[i].locked and app.puzzle.cells[i].type not in ("CROSS", "EMPTY"))
            row, col = app.puzzle.rc(index)
            before = app.state
            app.handle_click((app.grid_left + col * app.cell_size + app.cell_size // 2,
                              app.grid_top + row * app.cell_size + app.cell_size // 2))
            self.assertEqual(app.state[index], (before[index] + 1) % 4)
            self.assertEqual(sum(a != b for a, b in zip(before, app.state)), 1)

    def test_algorithm_buttons_dispatch_solver_and_restore_start_when_switching(self):
        app = self.app
        start = app.state
        solver = Mock(wraps=greedy_best_first)
        probe = SearchAlgorithm("probe", "Probe", solver, uses_heuristic=False)
        with patch.dict(ALGORITHMS, {"probe": probe}):
            app.draw()
            app.handle_click(app.algorithm_buttons["probe"].center)
            self.assertEqual(app.algorithm.key, "probe")
            app.handle_click(app.action_buttons["run"].center)
            self.finish_worker()
            solver.assert_called_once()
            self.assertEqual(solver.call_args.kwargs["start_state"], start)
            self.assertIsNone(solver.call_args.kwargs["max_depth"])
            self.assertTrue(app.search_result.found)
            app.draw()
            app.select_step(len(app.trace_steps) - 1)
            self.assertTrue(app.solved)
            app.select_algorithm("greedy")
        self.assertEqual(app.state, start)
        self.assertEqual(app.trace_steps, [])
        self.assertIsNone(app.search_result)
        self.assertEqual(app.algorithm.key, "greedy")

    def test_unavailable_algorithm_button_keeps_current_search(self):
        app = self.app
        pending = SearchAlgorithm("pending", "Pending", Mock(), available=False)
        with patch.dict(ALGORITHMS, {"pending": pending}):
            app.run_search()
            self.finish_worker()
            result = app.search_result
            app.draw()
            app.handle_click(app.algorithm_buttons["pending"].center)
        self.assertEqual(app.algorithm.key, "greedy")
        self.assertIs(app.search_result, result)
        pending.solver.assert_not_called()

    def test_depth_cutoff_does_not_claim_no_solution(self):
        self.app._finish_search(SearchResult("Depth-First Search", False, [], [], 1, 1, 1,
                                             0.0, 0.0, -1, "depth_limit"))
        self.assertEqual(self.app.status, "CHẠM GIỚI HẠN")

    def test_empty_rotation_table_distinguishes_depth_cutoff_goal_and_unrecorded_moves(self):
        app = self.app
        app.select_algorithm("dfs")
        trace = []
        result = depth_first_search(app.puzzle, max_nodes=400, max_depth=14,
                                    trace_callback=trace.append)
        cutoff = next(step for step in trace if step.depth_limited)
        self.assertEqual(cutoff.depth, 14)
        self.assertFalse(app.puzzle.is_goal(cutoff.state))
        cases = (
            (cutoff, "Chạm giới hạn độ sâu 14; dừng nhánh này."),
            (replace(cutoff, depth_limited=False), "Không có phép xoay được ghi ở bước này."),
        )
        for step, expected in cases:
            with self.subTest(expected=expected):
                app.trace_steps = [step]
                app._finish_search(result)
                app.select_step(0)
                with patch.object(app, "draw_text", wraps=app.draw_text) as draw_text:
                    app.draw()
                messages = [call.args[0] for call in draw_text.call_args_list]
                self.assertIn(expected, messages)
                self.assertNotIn("Đã đạt đích; không sinh thêm nhánh.", messages)

        trace = []
        result = depth_first_search(app.puzzle, start_state=app.solution_state,
                                    max_depth=0, trace_callback=trace.append)
        app.trace_steps = trace
        app._finish_search(result)
        app.select_step(0)
        with patch.object(app, "draw_text", wraps=app.draw_text) as draw_text:
            app.draw()
        messages = [call.args[0] for call in draw_text.call_args_list]
        self.assertIn("Đã đạt đích; không sinh thêm nhánh.", messages)


if __name__ == "__main__":
    unittest.main()
