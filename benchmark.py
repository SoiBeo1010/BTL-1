"""Thực nghiệm so sánh DFS và Greedy BFS trên Pipes Puzzle.

Mỗi thuật toán chạy 3 lượt cho mỗi kích thước (3×3 … 7×7).
Mỗi lượt chạy trong tiến trình con riêng biệt để đảm bảo đo bộ nhớ chính xác.
Bài toán cho mỗi lượt được sinh ngẫu nhiên (sparse) và lưu thành file JSON.
Kết quả: hai bảng CSV riêng cho DFS và Greedy BFS.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import statistics
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ---------------------------------------------------------------------------
# Cấu hình thực nghiệm
# ---------------------------------------------------------------------------
SIZES = [3, 4, 5, 6, 7]
RUNS_PER_SIZE = 3
SEEDS = [42, 123, 999]  # mỗi lượt dùng seed khác nhau
MAX_NODES = 10_000
ALGORITHMS = ["dfs", "greedy"]

# Thư mục lưu puzzle JSON sinh ra cho từng lượt
PUZZLE_DIR = os.path.join(BASE_DIR, "experiment_puzzles")
os.makedirs(PUZZLE_DIR, exist_ok=True)


# ===========================================================================
# Worker: chạy trong subprocess, nhận đường dẫn JSON + thuật toán
# ===========================================================================
def run_worker(args: argparse.Namespace) -> None:
    """Chạy trong tiến trình con: load puzzle, chạy thuật toán, in JSON kết quả."""
    from puzzle import PipesPuzzle
    from search import depth_first_search
    from search.greedy import greedy_best_first

    puzzle = PipesPuzzle.from_json(args.puzzle_path)
    max_depth = int(math.ceil((puzzle.rows * puzzle.cols) * 1.5))

    if args.algorithm == "dfs":
        res = depth_first_search(puzzle, max_nodes=args.max_nodes, max_depth=max_depth)
    else:
        res = greedy_best_first(puzzle, max_nodes=args.max_nodes, max_depth=max_depth)

    # Xác minh nghiệm
    is_valid = True
    if res.found:
        is_valid = _verify(puzzle, res.path, res.actions)

    data = {
        "found": res.found,
        "termination_reason": res.termination_reason,
        "depth": res.depth,
        "nodes_expanded": res.nodes_expanded,
        "nodes_generated": res.nodes_generated,
        "max_frontier": res.max_frontier,
        "time_ms": res.time_sec * 1000.0,
        "peak_kib": res.peak_memory_kb,
        "is_valid": is_valid,
    }
    print(json.dumps(data))


def _verify(puzzle, path, actions) -> bool:
    if not path or not puzzle.is_goal(path[-1]):
        return False
    if len(path) - 1 != len(actions):
        return False
    for i in range(len(actions)):
        s1, s2, act = path[i], path[i + 1], actions[i]
        for idx, cell in enumerate(puzzle.cells):
            if cell.locked and s1[idx] != s2[idx]:
                return False
        m = re.match(r"^R(\d+)\+(\d+)$", act)
        if not m:
            return False
        cell_idx, steps = int(m.group(1)), int(m.group(2))
        expected = list(s1)
        expected[cell_idx] = (s1[cell_idx] + steps) % 4
        if tuple(expected) != s2:
            return False
    return True


# ===========================================================================
# Master: sinh puzzle, gọi subprocess, thu thập kết quả
# ===========================================================================
def format_stat(mean_val: float, std_val: float, is_int: bool = False, dp: int = 1) -> str:
    if std_val == 0.0:
        return f"{int(round(mean_val))}" if is_int else f"{mean_val:.{dp}f}"
    if is_int:
        return f"{mean_val:.1f} ± {std_val:.1f}"
    return f"{mean_val:.{dp}f} ± {std_val:.{dp}f}"


def run_master() -> None:
    from generator import make_random_puzzle
    from puzzle import PipesPuzzle

    python_exe = sys.executable

    # -----------------------------------------------------------------------
    # Bước 1: Sinh puzzle cho mỗi (size, run) và lưu JSON
    # -----------------------------------------------------------------------
    print("=" * 80)
    print("  THỰC NGHIỆM SO SÁNH DFS vs GREEDY BFS")
    print(f"  max_nodes={MAX_NODES}  |  max_depth=(R×C)×1.5  |  {RUNS_PER_SIZE} lượt/kích thước")
    print("=" * 80)

    puzzle_paths: dict[tuple[int, int], str] = {}  # (size, run) -> path
    for size in SIZES:
        for run_idx, seed in enumerate(SEEDS):
            puzzle, _ = make_random_puzzle(size, size, seed=seed, sparse=True)
            fname = f"puzzle_{size}x{size}_run{run_idx + 1}_seed{seed}.json"
            fpath = os.path.join(PUZZLE_DIR, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(puzzle.to_dict(), f, indent=2, ensure_ascii=False)
            puzzle_paths[(size, run_idx)] = fpath

    print(f"\n[OK] Đã sinh {len(puzzle_paths)} file puzzle vào {PUZZLE_DIR}/\n")

    # -----------------------------------------------------------------------
    # Bước 2: Chạy từng thuật toán
    # -----------------------------------------------------------------------
    for algo in ALGORITHMS:
        algo_label = "Depth-First Search" if algo == "dfs" else "Greedy Best-First Search"
        print(f"\n{'─' * 80}")
        print(f"  THUẬT TOÁN: {algo_label}")
        print(f"{'─' * 80}")

        summary_rows = []
        raw_rows = []

        for size in SIZES:
            grid = f"{size}x{size}"
            N = size * size
            max_depth_val = int(math.ceil(N * 1.5))
            rotatable = sum(
                1 for c in PipesPuzzle.from_json(puzzle_paths[(size, 0)]).cells if not c.locked
            )

            print(f"\n  [{grid}]  N={N}, ô xoay={rotatable}, max_depth={max_depth_val}")
            run_results = []

            for run_idx in range(RUNS_PER_SIZE):
                ppath = puzzle_paths[(size, run_idx)]
                seed = SEEDS[run_idx]
                print(f"    Lượt {run_idx + 1} (seed={seed}): ", end="", flush=True)

                cmd = [
                    python_exe,
                    os.path.abspath(__file__),
                    "--worker",
                    "--algorithm", algo,
                    "--puzzle-path", ppath,
                    "--max-nodes", str(MAX_NODES),
                ]
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300,
                )
                if proc.returncode != 0:
                    print(f"LỖI!\n      stderr: {proc.stderr.strip()[:200]}")
                    run_results.append(None)
                    continue

                res = json.loads(proc.stdout.strip())
                run_results.append(res)

                status = "Đạt" if res["found"] else "Không đạt"
                print(
                    f"{status} | expanded={res['nodes_expanded']} | "
                    f"generated={res['nodes_generated']} | depth={res['depth']} | "
                    f"frontier={res['max_frontier']} | "
                    f"time={res['time_ms']:.2f}ms | mem={res['peak_kib']:.1f}KiB"
                )

                raw_rows.append({
                    "Kích thước": grid,
                    "Lượt": run_idx + 1,
                    "Seed": seed,
                    "File puzzle": os.path.basename(ppath),
                    "Kết quả": status,
                    "Expanded states": res["nodes_expanded"],
                    "Generated states": res["nodes_generated"],
                    "Solution depth": res["depth"] if res["found"] else "—",
                    "Maximum frontier size": res["max_frontier"],
                    "Thời gian (ms)": f"{res['time_ms']:.2f}",
                    "Bộ nhớ (KiB)": f"{res['peak_kib']:.1f}",
                })

            # Tổng hợp thống kê cho kích thước này
            valid = [r for r in run_results if r is not None]
            if not valid:
                summary_rows.append({
                    "Kích thước": grid,
                    "Số ô (N)": N,
                    "Ô xoay": rotatable,
                    "max_depth": max_depth_val,
                    "Kết quả": "Lỗi",
                    "Expanded states": "—",
                    "Generated states": "—",
                    "Solution depth": "—",
                    "Maximum frontier size": "—",
                    "Thời gian (ms)": "—",
                    "Bộ nhớ (KiB)": "—",
                })
                continue

            all_found = all(r["found"] for r in valid)
            any_found = any(r["found"] for r in valid)

            exp_vals = [r["nodes_expanded"] for r in valid]
            gen_vals = [r["nodes_generated"] for r in valid]
            front_vals = [r["max_frontier"] for r in valid]
            time_vals = [r["time_ms"] for r in valid]
            mem_vals = [r["peak_kib"] for r in valid]

            n = len(valid)
            stdev_f = lambda v: statistics.stdev(v) if n > 1 else 0.0

            if all_found:
                status_str = "Đạt"
                depth_vals = [r["depth"] for r in valid]
                depth_str = format_stat(statistics.mean(depth_vals), stdev_f(depth_vals), is_int=True)
            elif any_found:
                status_str = "Đạt một phần"
                depth_vals = [r["depth"] for r in valid if r["found"]]
                depth_str = format_stat(statistics.mean(depth_vals), stdev_f(depth_vals) if len(depth_vals) > 1 else 0.0, is_int=True) + " *"
            else:
                status_str = "Không đạt"
                depth_str = "—"

            summary_rows.append({
                "Kích thước": grid,
                "Số ô (N)": N,
                "Ô xoay": rotatable,
                "max_depth": max_depth_val,
                "Kết quả": status_str,
                "Expanded states": format_stat(statistics.mean(exp_vals), stdev_f(exp_vals), is_int=True),
                "Generated states": format_stat(statistics.mean(gen_vals), stdev_f(gen_vals), is_int=True),
                "Solution depth": depth_str,
                "Maximum frontier size": format_stat(statistics.mean(front_vals), stdev_f(front_vals), is_int=True),
                "Thời gian (ms)": format_stat(statistics.mean(time_vals), stdev_f(time_vals), dp=2),
                "Bộ nhớ (KiB)": format_stat(statistics.mean(mem_vals), stdev_f(mem_vals), dp=1),
            })

        # -------------------------------------------------------------------
        # Xuất CSV
        # -------------------------------------------------------------------
        summary_csv = os.path.join(BASE_DIR, f"benchmark_{algo}_summary.csv")
        with open(summary_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            w.writeheader()
            w.writerows(summary_rows)
        print(f"\n  [CSV] Bảng tổng hợp → {summary_csv}")

        raw_csv = os.path.join(BASE_DIR, f"benchmark_{algo}_raw.csv")
        with open(raw_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
            w.writeheader()
            w.writerows(raw_rows)
        print(f"  [CSV] Chi tiết từng lượt → {raw_csv}")

    print(f"\n{'=' * 80}")
    print("  HOÀN TẤT THỰC NGHIỆM")
    print(f"{'=' * 80}")


# ===========================================================================
# Entry point
# ===========================================================================
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--algorithm", choices=ALGORITHMS)
    parser.add_argument("--puzzle-path")
    parser.add_argument("--max-nodes", type=int, default=MAX_NODES)
    args = parser.parse_args()

    if args.worker:
        run_worker(args)
    else:
        run_master()


if __name__ == "__main__":
    main()

