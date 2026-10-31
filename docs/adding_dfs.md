# Hợp đồng DFS và tích hợp solver

DFS được hiện thực tại `search/dfs.py`, Greedy tại `search/greedy.py`. Chỉ thư mục
`search/` chứa hiện thực solver và kiểu kết quả. `search/runtime.py` dùng chung
node, trace, đo thời gian/bộ nhớ và dựng đường đi. UI và benchmark lấy solver từ
`search/registry.py`; `config.py` chứa preset và giới hạn chung.

## Chữ ký và kết quả

Cả hai solver giữ các tham số vị trí cũ: `puzzle`, `max_nodes`, `callback`,
`start_state`, `progress_callback`, `cancel_check`, `trace_callback`, `trace_limit`.
`max_depth` chỉ được truyền bằng tên. Giới hạn phải là số nguyên không âm;
CLI yêu cầu `max_nodes > 0`.

- `start_state`: bắt đầu từ trạng thái này nếu được truyền; không sửa puzzle.
- `callback(state, expanded, frontier_size)`: sau mỗi lần lấy một node hợp lệ ra xét.
- `progress_callback(state, expanded, generated, frontier_size)`: cập nhật UI.
- `cancel_check()`: được kiểm tra trước mỗi lượt và trong vòng sinh nhánh;
  một lần trả về đúng là đủ để dừng với `cancelled`.
- `trace_callback(step)`: giữ `trace_limit` lượt mở rộng đầu và luôn giữ bước đích.
- `max_depth=None`: không cắt độ sâu. UI và thực nghiệm giữ giá trị này cho Greedy;
  DFS dùng `default_max_depth(rows, cols) = ceil(1.5 * rows * cols)`.

`SearchResult` trả về `found`, `path`, `actions`, bộ đếm, thời gian, bộ nhớ và lý do dừng:

| Lý do | Ý nghĩa |
| --- | --- |
| `solved` | Trạng thái cuối đạt goal; `depth == len(actions) == len(path) - 1`. |
| `cancelled` | Có yêu cầu hủy. |
| `node_limit` | Bộ đếm sinh vượt `max_nodes`; giữ quy ước có thể vượt đúng một node. |
| `depth_limit` | Frontier đã hết nhưng có nhánh bị cắt độ sâu. |
| `exhausted` | Đã duyệt hết frontier mà không có cắt độ sâu. |

Thất bại trả `path=[]`, `actions=[]`, `depth=-1`. Trạng thái đầu đã giải trả độ sâu 0,
generated 1, expanded 0 và một trace đích số 0 nếu có callback. Dùng
`validate_solution()` để kiểm tra trạng thái đầu, đích, chiều dài và từng action
bằng `puzzle.successors()`.

`SearchResult.max_depth_reached` đo độ sâu lớn nhất của node thực sự được xét,
gồm node đích; vẫn được thu thập khi không bật trace hoặc không đặt giới hạn độ sâu.
Không dùng chỉ số đo này để cắt nhánh. `depth` chỉ là độ dài nghiệm cuối, nên có
thể nhỏ hơn `max_depth_reached`.

## Thứ tự và phát hiện trùng

DFS đọc successor theo thứ tự sinh, thu các node mới rồi đẩy ngược vào stack.
Vì vậy successor đầu tiên được xét trước. Heuristic chỉ dùng cho trace, không
tham gia chọn nhánh; khi không ghi trace, DFS không gọi heuristic.

Greedy dùng heap với khóa `(h, depth, node_id)`. Nếu không giới hạn độ sâu,
mỗi trạng thái chỉ được nhận lần đầu. Khi có giới hạn độ sâu, một đường ngắn hơn
đến cùng trạng thái được nhận lại vì nó còn nhiều bước để đi tiếp. Các đường dài
hơn hoặc bằng nhau vẫn bị bỏ qua. Node cũ còn nằm trong frontier được bỏ qua
khi lấy ra nếu đã có đường ngắn hơn thay thế.

`nodes_generated` tính số node được nhận, gồm trạng thái đầu và lần mở lại theo
đường ngắn hơn. `nodes_expanded` gồm cả đích và node bị cắt độ sâu, không gồm
entry lỗi thời bị bỏ qua. Frontier đếm số entry thực tế trong heap/stack.

## Trace và bộ nhớ

Mỗi đường được nhận có `node_id` duy nhất. Node giữ cha bất biến; mở lại trạng thái
không thay đổi cha/action trong các trace cũ. Candidate trùng có `heuristic=None`
và trỏ đến ID đã nhận cho trạng thái đó. Candidate mới hoặc được mở lại có ID mới.

Điểm heuristic của bước đang xét, candidate và frontier preview là điểm thật từ
puzzle. Preview giữ tối đa 5 node sẽ được xét tiếp và bỏ qua entry lỗi thời.
Hai bước mở rộng liên tiếp có thể thuộc hai nhánh khác nhau; UI tô ô xoay theo
`parent_state` thực tế.

Thời gian dùng `time.perf_counter()`, không gồm đọc/sinh input và dựng lại đường đi.
Bộ nhớ là KiB cấp phát Python do `tracemalloc` theo dõi, không phải RSS. Solver
chỉ dừng tracer do nó tự khởi động, kể cả khi callback phát sinh exception. Nếu
caller đã bật tracer, peak thuộc toàn bộ phiên theo dõi hiện hành của caller.

## Kiểm thử và benchmark

```powershell
python -B -m unittest discover -s tests -v
python -B benchmark.py --algorithm dfs --max-nodes 10000 --max-depth 14 --output dfs_results.csv
python -B benchmark.py --experiment --sizes 3 --seeds 42 123 999 --max-nodes 10000
```

`tests/test_solver_contract.py` kiểm tra hợp đồng chung, giới hạn, mở lại trạng thái,
hủy và vòng đời tracer. `tests/test_dfs.py` kiểm tra thứ tự DFS và trace thực tế;
`tests/test_search_trace.py` kiểm tra heap Greedy. Các test tích hợp UI và subprocess
nằm trong `tests/test_ui_trace.py` và `tests/test_experiments.py`.
