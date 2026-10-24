# Pipes Puzzle — Greedy Best-First Search

Demo trực quan bằng Pygame cho bài toán xoay các ống để tạo thành mạng kết nối hợp lệ. Project chỉ sử dụng **Greedy Best-First Search**, với frontier ưu tiên trạng thái có heuristic `h(n)` nhỏ nhất.

## Cấu trúc

```text
pipes_project/
├── puzzle.py        # Mô hình trạng thái, successor, goal test và heuristic
├── search.py        # Greedy Best-First Search
|-- generator.py     # Procedural random solvable layouts
├── main.py          # Giao diện Pygame và hoạt ảnh lời giải
├── benchmark.py     # Đo thời gian/bộ nhớ của Greedy trên 4 puzzle
├── puzzles/         # Puzzle mẫu 3x3 đến 6x6
└── requirements.txt
```

## Cài đặt và chạy

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Chạy benchmark:

```powershell
python benchmark.py
```

## Điều khiển

| Phím | Chức năng |
|------|-----------|
| `1` / `2` / `3` / `4` | Chọn puzzle Tiny, Easy, Medium hoặc Hard |
| `N` | Tao layout ngau nhien va seed moi cho puzzle dang chon |
| `M` | Chuyển Dense / Sparse: nhiều nhánh-vòng hoặc mạng thưa dạng cây |
| `T` | Toggle Midnight / Aurora palette |
| `G` | Chạy Greedy Best-First Search và tự động phát lời giải |
| `S` | Chạy một bước; nếu chưa tìm kiếm thì bắt đầu tìm lời giải |
| `Space` | Tạm dừng / tiếp tục hoạt ảnh |
| `R` | Đặt lại puzzle |
| `C` | Cancel the current solution animation |
| Click ô | Xoay ống 90 độ |
| `Esc` / `Q` | Thoát |

Trong giao diện, phần xanh là đầu nối khớp, còn đỏ là đầu nối chưa khớp. Bảng điều khiển bên phải hiển thị `h(n)`, số mismatch, số node đã mở rộng, frontier lớn nhất, thời gian và số bước.

During `G`, Greedy runs in a background worker. The expanded, generated, frontier and elapsed-time counters update live while the search is running.
The `FRONTIER MAX` display counts smoothly, then follows the solution animation so it reaches the recorded maximum on the final pipe rotation. Its counting rate adapts to the remaining steps and pauses with the animation; large values can advance by multiple units per frame. If no rotation is needed or no solution is found, the final maximum is shown immediately.

## Random puzzles

Every launch, size change, or press of `N` creates a new random seed and layout. The generator builds a connected network with branches and loops from a fixed source in the center, then scrambles a bounded number of tiles. Sparse mode keeps every cell occupied by a pipe, omits loops, and chooses rotations that break the most existing connections. It changes about a third of the tiles (at least four on small boards), leaving fewer matching connections at the start without adding empty cells. Press `M` to switch between Sparse and Dense. The source is the only fixed tile; every other non-cross tile can rotate. Cross pipes are skipped because rotating them does not change their connections.

Each scramble starts from a valid solution, so Greedy Best-First Search always has a solution path.

## Heuristic

`h(n)` bằng số cặp kết nối không khớp cộng thêm phạt cho số ô chưa nối được về nguồn. Trạng thái đích phải vừa không còn mismatch vừa tạo thành một mạng liên thông từ nguồn. Greedy Best-First luôn mở rộng trạng thái có `h(n)` thấp nhất trước; thuật toán ưu tiên tốc độ tìm lời giải và không đảm bảo số bước tối ưu.
