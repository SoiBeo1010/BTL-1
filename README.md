# Pipes Puzzle — DFS và Greedy Best-First Search

Demo trực quan bằng Pygame cho bài toán xoay các ống để tạo thành mạng kết nối hợp lệ. **Greedy Best-First Search** ưu tiên trạng thái có heuristic `h(n)` nhỏ nhất. **Depth-First Search (DFS)** dùng ngăn xếp LIFO và không dùng heuristic để chọn nhánh. Cả hai dùng chung kiểu kết quả, trace, đo thời gian/bộ nhớ và registry.

## Cấu trúc

```text
pipes_project/
├── puzzle.py          # Mô hình trạng thái, successor, goal test và heuristic
├── config.py          # Danh sách puzzle và giới hạn dùng chung
├── search/
│   ├── __init__.py    # API công khai; giữ tương thích import cũ
│   ├── common.py      # State, SearchResult, trace, callback, dựng lại lời giải
│   ├── greedy.py      # Thuật toán Greedy Best-First hiện có
│   ├── dfs.py         # Blind DFS, thăm successor theo thứ tự sinh
│   ├── runtime.py     # Node, trace, đo thời gian/bộ nhớ và dựng kết quả
│   └── registry.py    # Danh sách thuật toán dùng chung cho UI và benchmark
├── generator.py       # Sinh puzzle ngẫu nhiên có lời giải
├── main.py            # Giao diện Pygame, phát lại tìm kiếm và lời giải
├── benchmark.py       # Đo thuật toán đã chọn trên 5 puzzle
├── experiments.py     # Sinh input, chạy subprocess và tổng hợp thực nghiệm
├── docs/adding_dfs.md # Hợp đồng solver, quy tắc DFS và trace
├── puzzles/           # Puzzle mẫu 3x3, 4x4, 5x5, 6x6 và 7x7
├── tests/             # Kiểm tra thuật toán và điều khiển UI
├── report/            # Báo cáo cục bộ, được loại khỏi Git
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
python benchmark.py --algorithm greedy --output greedy_results.csv
python benchmark.py --algorithm dfs --max-nodes 10000 --max-depth 14 --output dfs_results.csv
```

Các lệnh trên đo nhóm JSON trong `puzzles/`; CSV có cột `algorithm` và `termination_reason`. Giới hạn độ sâu chỉ áp dụng khi truyền `--max-depth`.

Thực nghiệm trên puzzle Sparse sinh bằng các seed cố định, cùng input cho cả hai thuật toán, mỗi lượt trong một tiến trình mới:

```powershell
python benchmark.py --experiment
python benchmark.py --experiment --sizes 3 4 --seeds 42 123 999 --max-nodes 10000
```

Mặc định thực nghiệm dùng seed 42, 123, 999 trên các cỡ 3×3–7×7; `--algorithm dfs` hoặc `--algorithm greedy` chọn một solver. JSON được lưu trong `experiment_puzzles/`, CSV mới trong `experiment_results/`; có thể đổi bằng `--puzzle-dir` và `--output-dir`. DFS mặc định giới hạn độ sâu ở `ceil(1.5 * rows * cols)`; Greedy mặc định dùng `max_depth=None`. `--max-depth` đặt giới hạn cụ thể khi cần. CLI và worker đều dùng registry.

CSV tổng hợp ghi số lượt yêu cầu, thành công và lỗi riêng. Độ sâu chỉ tổng hợp các lượt có nghiệm; dấu `*` chỉ một phần số lượt tìm được nghiệm. Lỗi worker vẫn có dòng trong CSV chi tiết, kể cả khi tất cả lượt đều lỗi. Dữ liệu DFS đang lưu thuộc đợt đo trước refactor. GBFS đã được đo lại trên 15 JSON có sẵn, mỗi JSON năm lần trong tiến trình mới, tổng cộng 75 lượt; số liệu chi tiết và hash đầu vào/mã nguồn nằm trong `experiment_results/benchmark_greedy_measurements.json`. Đợt đo GBFS này dùng `max_nodes=10000`, `max_depth=None`; các chỉ số tìm kiếm tổng hợp trên ba input mỗi kích thước, thời gian/bộ nhớ trên 15 lượt đo mỗi kích thước.

## Quy tắc tìm kiếm dùng chung

DFS và Greedy đều hoạt động trên UI và benchmark. Chữ ký solver được mô tả trong `search/common.py`; `max_depth` là tham số chỉ truyền bằng tên. Hướng dẫn chi tiết nằm ở [docs/adding_dfs.md](docs/adding_dfs.md).

DFS đẩy danh sách con theo thứ tự ngược, nên successor được sinh đầu tiên sẽ được xét trước. Với giới hạn độ sâu, cả hai solver cho phép xét lại trạng thái khi tìm được đường ngắn hơn để không bỏ sót nhánh còn đủ độ sâu. Mỗi đường được chấp nhận có node ID và cha riêng; `nodes_generated` tính cả các lần mở lại này, trạng thái đầu và giữ quy ước dừng khi vượt `max_nodes` một node.

Kết quả dừng phân biệt `solved`, `cancelled`, `node_limit`, `depth_limit` và `exhausted`. UI dùng cùng công thức giới hạn độ sâu với thực nghiệm; chạm giới hạn không được hiển thị như đã chứng minh vô nghiệm.

`max_depth` là giới hạn tùy chọn đặt trước; `SearchResult.max_depth_reached` là độ sâu lớn nhất của node thực sự được lấy ra xét, gồm đích, đo được cả khi `max_depth=None`. Chỉ số này khác độ sâu lời giải: Greedy có thể xét một nhánh sâu rồi trả về nghiệm trên đường ngắn hơn. CSV dùng cột `Max depth reached` hoặc `max_depth_reached` để phân biệt hai ý nghĩa.

UI gọi thuật toán qua `run_search()`, benchmark lấy solver từ `search/registry.py`. Greedy và DFS dùng chung `SearchResult`, callback tiến độ, hủy và bản ghi tìm kiếm nên thành viên làm DFS có thể tập trung vào module riêng. Các import cũ như `from search import greedy_best_first` vẫn dùng được.

## Điều khiển

| Phím | Chức năng |
|------|-----------|
| `1` / `2` / `3` / `4` | Chọn lưới 3×3, 4×4, 5×5 hoặc 6×6 |
| `5` | Chọn lưới lớn 7×7 |
| `N` | Tao layout ngau nhien va seed moi cho puzzle dang chon |
| `M` | Chuyển Dense / Sparse: nhiều nhánh-vòng hoặc mạng thưa dạng cây |
| `T` | Toggle Midnight / Aurora palette |
| `G` | Chạy thuật toán đang chọn, ghi quá trình tìm kiếm và mở bản ghi ở bước đầu, tạm dừng |
| `S` / `→` | Xem bước tiếp theo; nếu chưa tìm kiếm thì bắt đầu chạy AI |
| `←` | Quay lại bước trước |
| `Home` / `End` | Về đầu / cuối bản ghi đang xem |
| `Space` | Phát / tạm dừng; phát lại từ đầu khi đang ở bước cuối |
| `Tab` | Đổi giữa quá trình tìm kiếm và đường đi lời giải (khi có lời giải) |
| `R` | Đặt lại puzzle |
| `C` | Hủy tìm kiếm hoặc dừng phát; giữ các bước đã ghi để xem lại |
| Click ô | Xoay ống 90 độ khi chơi thủ công; nhấn `R` để về chơi sau khi xem AI |
| `Esc` / `Q` | Thoát |

Trong giao diện, các đầu nối khớp tạo thành đường ống xanh ngọc liên tục, có quầng sáng và điểm sáng nhỏ. Đầu hở được đánh dấu hồng; hình thoi hồng ở góc ô báo lỗi kết nối. Màu nút giữa phân biệt loại ống: vàng cho đầu bịt, xanh dương cho ống thẳng, tím cho ống góc, hồng cho chữ T và xanh ngọc cho ngã tư. Ký hiệu `G` đánh dấu gốc nguồn cố định. Các ô không thể xoay (ô bị khóa, ngã tư và ô trống) có nền nâu kẻ chéo, viền cam và biểu tượng khóa nổi bật; chú thích “Khóa: không thể xoay” nằm phía trên bàn chơi. Viền vàng đánh dấu ô vừa được xoay. Các hàng/cột được đánh số từ 1 để đối chiếu với bảng phép xoay.

## Xem AI giải từng bước

Nhấn **Chạy AI** (`G`), sau đó dùng **Lùi / Tiến**, **Phát**, hoặc kéo thanh tiến trình. Nút tốc độ chuyển giữa `0.5x`, `1x`, `2x` và `5x`. Chọn tab để xem:

- **Quá trình tìm kiếm**: mỗi bản ghi tương ứng một trạng thái thực sự được lấy khỏi frontier. UI hiển thị node, trạng thái cha, phép xoay từ cha, độ sâu, cách tính `h(n)`, các nhánh mới/trùng và tối đa 5 node sẽ được xét tiếp. Cuộn trong bảng phép xoay để xem hết các nhánh. Với Greedy, bảng xếp theo `h(n)`; thuật toán ưu tiên `h(n)` nhỏ nhất, sau đó độ sâu nhỏ hơn và thứ tự thêm vào hàng đợi. Với DFS, bảng giữ thứ tự sinh nhánh và hiển thị ngăn xếp LIFO; heuristic chỉ là thông tin tham khảo. `Δh` là điểm của nhánh con trừ điểm của node đang xét.
- **Đường đi lời giải**: các phép xoay được truy ngược từ đích về trạng thái ban đầu. Click một dòng để đến bước đó. Đây là đường đi AI tìm được, có thể bỏ qua nhiều nhánh đã xét trong quá trình tìm kiếm.

Khi hai node được mở rộng liên tiếp thuộc hai nhánh khác nhau, viền vàng vẫn thể hiện phép xoay từ **cha thực sự** của node đang xem. Các chỉ số “Tại bước này” lấy từ bản ghi tương ứng; dòng “Tổng” là kết quả của toàn bộ lần chạy, không nội suy theo hoạt ảnh.

Thuật toán chạy trong luồng nền nên có thể xem bản ghi ngay khi tìm kiếm còn chạy. Chọn thuật toán bằng các nút ở đầu cửa sổ; đổi thuật toán sẽ đưa bàn chơi về trạng thái bắt đầu của lần tìm kiếm vừa xem để dễ đối chiếu. Để giới hạn bộ nhớ, UI lưu tối đa **2.000 lượt mở rộng đầu tiên và trạng thái đích nếu tìm thấy sau đó**; giao diện thông báo khi vượt giới hạn này. Việc tìm kiếm vẫn tiếp tục và đường đi lời giải giữ đầy đủ các phép xoay. Benchmark không bật ghi bản truy vết.

Chạy kiểm tra tự động (bao gồm UI với màn hình giả lập):

```powershell
python -B -m unittest discover -s tests -v
```

## Random puzzles

Every launch, size change, or press of `N` creates a new random seed and layout. The generator builds a connected network with branches and loops from a fixed source in the center, then scrambles a bounded number of tiles. Sparse mode keeps every cell occupied by a pipe, omits loops, and chooses rotations that break the most existing connections. It changes about a third of the tiles (at least four on small boards), leaving fewer matching connections at the start without adding empty cells. Press `M` to switch between Sparse and Dense. The source is the only fixed tile; every other non-cross tile can rotate. Cross pipes are skipped because rotating them does not change their connections.

Five grid sizes are available: 3×3, 4×4, 5×5, 6×6 and 7×7. Tiles and source/lock badges scale to keep the entire board visible. Larger generated networks can reach the search limit before Greedy finds a solution; the UI keeps the recorded search steps for review. The JSON fixtures used by the command-line benchmark contain perimeter networks with locked empty interiors, so their difficulty differs from full generated boards.

Each scramble starts from a valid solution, so Greedy Best-First Search always has a solution path.

## Heuristic

`h(n)` bằng số cặp kết nối không khớp cộng thêm phạt cho số ô chưa nối được về nguồn. Trạng thái đích phải vừa không còn mismatch vừa tạo thành một mạng liên thông từ nguồn. Greedy Best-First luôn mở rộng trạng thái có `h(n)` thấp nhất trước; thuật toán ưu tiên tốc độ tìm lời giải và không đảm bảo số bước tối ưu.

## Báo cáo

Thư mục `report/` chứa báo cáo và tài liệu cục bộ, được bỏ qua bởi `.gitignore`. Bản PDF hiện tại và gói nguồn Overleaf nằm trong `report/output/`; nguồn LaTeX ở `report/latex/`, script ở `report/scripts/`, số liệu ở `report/data/`. Các bản cũ được giữ trong `report/archive/`, còn file biên dịch trung gian nằm ở `report/build/`.

Khi có đủ tài liệu cục bộ và đã cài XeLaTeX hoặc Tectonic, xuất lại báo cáo từ thư mục gốc project:

```powershell
python -B report/scripts/build_report.py
```

Hướng dẫn chỉnh sửa và tái lập số liệu nằm trong `report/README.md`. Các lượt đo thực nghiệm được giữ nguyên khi sắp xếp lại thư mục.
