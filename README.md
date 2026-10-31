# Pipes Puzzle — DFS và Greedy

Ứng dụng Python/Pygame mô phỏng bài toán xoay ống, hỗ trợ giải bằng DFS hoặc Greedy Best-First Search và xem lại từng bước tìm kiếm.

## Cài đặt và chạy

Cần **Python 3.10 trở lên** (đã kiểm thử với Python 3.13) và màn hình đồ họa. Cài Git để tải mã bằng lệnh dưới đây, hoặc tải ZIP từ GitHub rồi giải nén.

```bash
git clone https://github.com/SoiBeo1010/BTL-1.git
cd BTL-1
```

Chạy các lệnh trong thư mục chứa `main.py` và `requirements.txt`.

**Windows — PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

**Linux / macOS:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Cửa sổ trò chơi sẽ mở. Chọn **DFS** hoặc **Greedy**, rồi nhấn **Chạy AI**. Nếu Linux báo thiếu `venv`, cài gói `python3-venv` bằng trình quản lý gói của hệ điều hành.

## Cách sử dụng

| Thao tác | Chức năng |
| --- | --- |
| Nhấp ô | Xoay ống khi chơi thủ công |
| `1`–`5` | Chọn kích thước từ 3×3 đến 7×7 |
| `N` / `M` | Tạo bài mới / chuyển mạng dày hoặc thưa |
| `G` | Chạy thuật toán đang chọn |
| `←` / `→` / `Space` | Lùi / tiến / phát hoặc tạm dừng |
| `Tab` | Đổi giữa quá trình tìm kiếm và đường đi lời giải |
| `R` / `C` | Đặt lại bài / hủy tìm kiếm |
| `Esc` / `Q` | Thoát |

## Kiểm thử và thực nghiệm

Trên Windows:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe benchmark.py --algorithm greedy --max-nodes 10000 --output greedy_results.csv
.\.venv\Scripts\python.exe benchmark.py --experiment --sizes 3 4 --seeds 42 123 999 --max-nodes 10000
```

Trên Linux/macOS, thay `.\.venv\Scripts\python.exe` bằng `.venv/bin/python`.

Lệnh thứ hai đo các bài mẫu trong `puzzles/`; đổi `--algorithm greedy` thành `--algorithm dfs` để chạy DFS. Lệnh thứ ba sinh bài mới cho cả hai thuật toán, lưu JSON vào `experiment_puzzles/` và CSV vào `experiment_results/`; các file cùng tên sẽ được ghi lại.

DFS mặc định giới hạn độ sâu khi chạy giao diện hoặc thực nghiệm; Greedy mặc định không giới hạn độ sâu. `max_depth_reached` là độ sâu lớn nhất đã xét. Chạm giới hạn tìm kiếm không có nghĩa bài toán vô nghiệm.

Mô hình bài toán nằm trong `puzzle.py`, thuật toán trong `search/`, cấu hình trong `config.py`. Xem [quy tắc thuật toán và truy vết](docs/adding_dfs.md) để tìm hiểu thêm.
