# Pipes Puzzle — Greedy và khung tích hợp DFS

Demo trực quan bằng Pygame cho bài toán xoay các ống để tạo thành mạng kết nối hợp lệ. **Greedy Best-First Search** đã hoạt động, với frontier ưu tiên trạng thái có heuristic `h(n)` nhỏ nhất. **Depth-First Search (DFS)** có module và giao diện tích hợp sẵn để một thành viên khác triển khai.

## Cấu trúc

```text
pipes_project/
├── puzzle.py          # Mô hình trạng thái, successor, goal test và heuristic
├── search/
│   ├── __init__.py    # API công khai; giữ tương thích import cũ
│   ├── common.py      # State, SearchResult, trace, callback, dựng lại lời giải
│   ├── greedy.py      # Thuật toán Greedy Best-First hiện có
│   ├── dfs.py         # Khung hàm DFS dành cho thành viên phụ trách
│   └── registry.py    # Danh sách thuật toán dùng chung cho UI và benchmark
├── generator.py       # Sinh puzzle ngẫu nhiên có lời giải
├── main.py            # Giao diện Pygame, phát lại tìm kiếm và lời giải
├── benchmark.py       # Đo thuật toán đã chọn trên 4 puzzle
├── docs/adding_dfs.md # Hướng dẫn triển khai, kiểm thử và ghép DFS
├── puzzles/           # Puzzle mẫu 3x3 đến 6x6
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
```

CSV có cột `algorithm` để phân biệt kết quả khi so sánh thuật toán. Có thể giới hạn tìm kiếm bằng `--max-nodes`.

## Bổ sung DFS và làm việc nhóm

Thành viên phụ trách triển khai `depth_first_search()` trong [search/dfs.py](search/dfs.py) theo hợp đồng dùng chung và hướng dẫn tại [docs/adding_dfs.md](docs/adding_dfs.md), sau đó đổi `IMPLEMENTED = True`. Khi khởi động lại, nút DFS trên UI tự được bật và benchmark nhận `--algorithm dfs`. Hiện DFS hiển thị “sắp có” và chưa thể chạy.

UI gọi thuật toán qua `run_search()`, benchmark lấy solver từ `search/registry.py`. Greedy và DFS dùng chung `SearchResult`, callback tiến độ, hủy và bản ghi tìm kiếm nên thành viên làm DFS có thể tập trung vào module riêng. Các import cũ như `from search import greedy_best_first` vẫn dùng được.

## Điều khiển

| Phím | Chức năng |
|------|-----------|
| `1` / `2` / `3` / `4` | Chọn puzzle Tiny, Easy, Medium hoặc Hard |
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

- **Quá trình tìm kiếm**: mỗi bản ghi tương ứng một trạng thái thực sự được lấy khỏi frontier. UI hiển thị node, trạng thái cha, phép xoay từ cha, độ sâu, cách tính `h(n)`, các nhánh mới/trùng và tối đa 5 node sẽ được xét tiếp. Cuộn trong bảng phép xoay để xem hết các nhánh. Với Greedy, bảng xếp theo `h(n)`; thuật toán ưu tiên `h(n)` nhỏ nhất, sau đó độ sâu nhỏ hơn và thứ tự thêm vào hàng đợi. Khi DFS được triển khai, bảng giữ thứ tự sinh nhánh và hiển thị ngăn xếp LIFO; heuristic chỉ là thông tin tham khảo. `Δh` là điểm của nhánh con trừ điểm của node đang xét.
- **Đường đi lời giải**: các phép xoay được truy ngược từ đích về trạng thái ban đầu. Click một dòng để đến bước đó. Đây là đường đi AI tìm được, có thể bỏ qua nhiều nhánh đã xét trong quá trình tìm kiếm.

Khi hai node được mở rộng liên tiếp thuộc hai nhánh khác nhau, viền vàng vẫn thể hiện phép xoay từ **cha thực sự** của node đang xem. Các chỉ số “Tại bước này” lấy từ bản ghi tương ứng; dòng “Tổng” là kết quả của toàn bộ lần chạy, không nội suy theo hoạt ảnh.

Thuật toán chạy trong luồng nền nên có thể xem bản ghi ngay khi tìm kiếm còn chạy. Chọn thuật toán bằng các nút ở đầu cửa sổ; đổi thuật toán sẽ đưa bàn chơi về trạng thái bắt đầu của lần tìm kiếm vừa xem để dễ đối chiếu. Để giới hạn bộ nhớ, UI lưu tối đa **2.000 lượt mở rộng đầu tiên và trạng thái đích nếu tìm thấy sau đó**; giao diện thông báo khi vượt giới hạn này. Việc tìm kiếm vẫn tiếp tục và đường đi lời giải giữ đầy đủ các phép xoay. Benchmark không bật ghi bản truy vết.

Chạy kiểm tra tự động (bao gồm UI với màn hình giả lập):

```powershell
python -B -m unittest discover -s tests -v
```

## Random puzzles

Every launch, size change, or press of `N` creates a new random seed and layout. The generator builds a connected network with branches and loops from a fixed source in the center, then scrambles a bounded number of tiles. Sparse mode keeps every cell occupied by a pipe, omits loops, and chooses rotations that break the most existing connections. It changes about a third of the tiles (at least four on small boards), leaving fewer matching connections at the start without adding empty cells. Press `M` to switch between Sparse and Dense. The source is the only fixed tile; every other non-cross tile can rotate. Cross pipes are skipped because rotating them does not change their connections.

Each scramble starts from a valid solution, so Greedy Best-First Search always has a solution path.

## Heuristic

`h(n)` bằng số cặp kết nối không khớp cộng thêm phạt cho số ô chưa nối được về nguồn. Trạng thái đích phải vừa không còn mismatch vừa tạo thành một mạng liên thông từ nguồn. Greedy Best-First luôn mở rộng trạng thái có `h(n)` thấp nhất trước; thuật toán ưu tiên tốc độ tìm lời giải và không đảm bảo số bước tối ưu.

## Báo cáo

Thư mục `report/` chứa báo cáo và tài liệu cục bộ, được bỏ qua bởi `.gitignore` và không đưa vào các commit tiếp theo. Nếu bạn đã tạo báo cáo trên máy, các file vẫn được giữ nguyên tại đây.
