# Hướng dẫn triển khai DFS

Greedy đã được tách vào `search/greedy.py`. Thành viên làm DFS triển khai trong
`search/dfs.py` và bổ sung kiểm thử trong `tests/test_dfs.py` để hạn chế đụng file
với người làm UI hoặc Greedy.

## Bắt đầu và ghép mã

Nhận commit chứa cấu trúc mới từ nhánh chung trước khi tạo nhánh làm DFS:

```powershell
git switch -c feature/dfs
```

1. Giữ chữ ký `depth_first_search()` đã khai báo trong `search/dfs.py`.
2. Triển khai DFS bằng ngăn xếp LIFO và kiểm tra trạng thái trùng. Không gọi Greedy
   thay cho DFS; heuristic chỉ phục vụ thông tin hiển thị.
3. Bổ sung các kiểm thử hành vi bên dưới và đổi `IMPLEMENTED = True` trong cùng
   module khi thuật toán đã hoạt động.
4. Chạy kiểm thử và benchmark, commit rồi push nhánh DFS:

```powershell
python -B -m unittest discover -s tests -v
python -B benchmark.py --algorithm dfs --max-nodes 10000 --output dfs_results.csv
git add search/dfs.py tests/test_dfs.py
git commit -m "Implement depth-first search for Pipes"
git push -u origin feature/dfs
```

Tạo pull request vào nhánh chung. Không cần sửa `main.py`, `benchmark.py`,
`search/registry.py` hoặc `search/__init__.py` để bật DFS. Sau khi ghép mã và mở lại
ứng dụng, nút DFS sẽ tự được bật. Nút G và điều khiển phát lại dùng thuật toán
đang chọn. Khi đổi thuật toán, UI trả về trạng thái bắt đầu tìm kiếm để so sánh.

## Giao diện dùng chung

Import dữ liệu từ `search.common` và mô hình từ `puzzle`; không import từ `main`
hoặc `search.greedy`. Có thể dùng `ParentMap` và `reconstruct_path()` để dựng
lời giải. Tham khảo Greedy để thống nhất thống kê và callback.

| Tham số | Yêu cầu |
| --- | --- |
| `puzzle` | Dùng `initial_state()`, `is_goal(state)` và `successors(state)`. Không sửa `puzzle.cells`. |
| `start_state` | Nếu khác `None`, bắt đầu đúng trạng thái này, kể cả khi bàn chơi đã được xoay thủ công. |
| `max_nodes` | Giới hạn số trạng thái sinh ra, tính cả trạng thái đầu. Giống Greedy hiện có, dừng sau khi `nodes_generated > max_nodes`; có thể vượt một trạng thái. |
| `callback` | Callback cũ: `(state, expanded, frontier_size)` sau khi lấy node ra khỏi frontier. |
| `progress_callback` | `(state, expanded, generated, frontier_size)` để UI cập nhật thống kê. |
| `cancel_check` | Kiểm tra trong vòng lặp tìm kiếm và khi sinh nhánh; dừng sớm để UI có thể reset hoặc hủy. |
| `trace_callback` | Nhận một `SearchTraceStep` cho mỗi lượt mở rộng được ghi. |
| `trace_limit` | Giữ các lượt mở rộng đầu tiên đến giới hạn và luôn ghi trạng thái đích, kể cả khi tìm thấy sau giới hạn. Không cắt ngắn việc tìm kiếm hoặc lời giải. |

`SearchResult` cần có `algorithm="Depth-First Search"`, đường đi `path`, phép xoay
`actions`, thống kê mở rộng/sinh trạng thái/frontier, thời gian và bộ nhớ. Giữ
nguyên chuỗi action từ `puzzle.successors()`, ví dụ `R5+2`, để UI mô tả đúng ô xoay.
Đo thời gian bằng `time.perf_counter()` và bộ nhớ bằng `tracemalloc` như Greedy.

- Thành công: `found=True`, `path[0]` là trạng thái đầu, trạng thái cuối đạt đích,
  `len(actions) == depth == len(path) - 1`, `termination_reason="solved"`.
- Thất bại: `found=False`, `path=[]`, `actions=[]`, `depth=-1`; phân biệt
  `"cancelled"`, `"node_limit"` và `"exhausted"`.
- Trạng thái đầu đã đạt đích: trả lời giải độ sâu 0, sinh 1 trạng thái, mở rộng 0;
  nếu có callback trace, phát một bản ghi đích số 0.

## Bản ghi để phát lại trên UI

- Mỗi trạng thái mới có `node_id` duy nhất theo thứ tự sinh, bắt đầu từ 0;
  trạng thái trùng dùng lại ID. Chỉ thêm trạng thái mới vào ngăn xếp.
- `parent_state`, `parent_id` và `action` phải trỏ đến cha thực sự của node.
  Hai node được mở rộng liên tiếp có thể thuộc hai nhánh khác nhau.
- `number` là số lượt mở rộng; `depth` là độ sâu theo cha. `frontier_before` là
  kích thước ngay trước khi pop, `frontier_after` là sau khi xử lý node.
- `candidates` ghi các nhánh mới và nhánh trùng theo thứ tự sinh. Nhánh trùng có
  `duplicate=True`, `heuristic=None`; nhánh mới ghi điểm heuristic để UI tham khảo.
- `SearchTraceStep.heuristic` và `FrontierEntry.heuristic` vẫn chứa
  `puzzle.heuristic(state)` cho phần thông tin; DFS không dùng giá trị này để chọn
  node. UI hiển thị quy tắc LIFO và giữ thứ tự sinh nhánh khi chọn DFS.
- `frontier_preview` chứa tối đa 5 node sắp được mở rộng, theo thứ tự pop thực tế:
  với stack dạng list, đọc từ cuối về đầu. Phần tử đầu là node sẽ xét tiếp.
- `generated` và `max_frontier` là số tích lũy tại thời điểm ghi bước đó.

Quy định rõ thứ tự push successor trong mã và kiểm thử, vì LIFO làm đảo thứ tự
duyệt so với thứ tự push. DFS không cần tìm lời giải ngắn nhất.

## Kiểm thử cần có

1. Một puzzle nhỏ có lời giải: mọi bước đi thuộc `successors()` của trạng thái
   trước, action khớp, ô khóa không đổi và trạng thái cuối đạt đích.
2. Một đồ thị nhỏ có nhiều nhánh/cycle: kiểm tra thứ tự mở rộng LIFO thực tế và
   việc bỏ qua trạng thái trùng, tránh kiểm thử chỉ dựa vào kết quả tìm được đích.
3. Dùng `start_state` đã giải, trạng thái đầu khác mặc định, hủy, giới hạn node và
   bài toán hết trạng thái mà không có lời giải.
4. Trace chứa đúng cha, node ID, candidate và thứ tự preview; đặt `trace_limit=1`
   vẫn giữ bước đích và đầy đủ lời giải. So sánh kết quả có/không ghi trace.

`tests/test_search_trace.py` và `tests/test_ui_trace.py` là ví dụ kiểm tra hành vi
hiện có. `report/` chỉ nằm cục bộ và được `.gitignore` bỏ qua; không cần đưa báo
cáo vào commit thuật toán.
