# Pipes Puzzle — Greedy Best-First Search

Demo trực quan bằng Pygame cho bài toán xoay các ống để tạo thành mạng kết nối hợp lệ. Project chỉ sử dụng **Greedy Best-First Search**, với frontier ưu tiên trạng thái có heuristic `h(n)` nhỏ nhất.

## Cấu trúc

```text
pipes_project/
├── puzzle.py        # Mô hình trạng thái, successor, goal test và heuristic
├── search.py        # Greedy Best-First Search
|-- generator.py     # Procedural random solvable layouts
├── main.py          # Giao diện Pygame, xem từng bước tìm kiếm và lời giải
├── benchmark.py     # Đo thời gian/bộ nhớ của Greedy trên 4 puzzle
├── puzzles/         # Puzzle mẫu 3x3 đến 6x6
├── tests/           # Kiểm tra bản ghi tìm kiếm và điều khiển UI
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
| `G` | Chạy Greedy, ghi quá trình tìm kiếm và mở bản ghi ở bước đầu, tạm dừng |
| `S` / `→` | Xem bước tiếp theo; nếu chưa tìm kiếm thì bắt đầu chạy AI |
| `←` | Quay lại bước trước |
| `Home` / `End` | Về đầu / cuối bản ghi đang xem |
| `Space` | Phát / tạm dừng; phát lại từ đầu khi đang ở bước cuối |
| `Tab` | Đổi giữa quá trình tìm kiếm và đường đi lời giải (khi có lời giải) |
| `R` | Đặt lại puzzle |
| `C` | Hủy tìm kiếm hoặc dừng phát; giữ các bước đã ghi để xem lại |
| Click ô | Xoay ống 90 độ khi chơi thủ công; nhấn `R` để về chơi sau khi xem AI |
| `Esc` / `Q` | Thoát |

Trong giao diện, phần xanh là đầu nối khớp, còn đỏ là đầu nối chưa khớp. Viền vàng đánh dấu ô vừa được xoay. Các hàng/cột được đánh số từ 1 để đối chiếu với bảng phép xoay.

## Xem AI giải từng bước

Nhấn **Chạy AI** (`G`), sau đó dùng **Lùi / Tiến**, **Phát**, hoặc kéo thanh tiến trình. Nút tốc độ chuyển giữa `0.5x`, `1x`, `2x` và `5x`. Chọn tab để xem:

- **Quá trình tìm kiếm**: mỗi bản ghi tương ứng một trạng thái thực sự được lấy khỏi hàng đợi. UI hiển thị node, trạng thái cha, phép xoay từ cha, độ sâu, cách tính `h(n)`, các nhánh mới/trùng và 5 node ưu tiên tiếp theo. Cuộn trong bảng phép xoay để xem hết các nhánh; bảng xếp theo `h(n)`. `Δh` là điểm của nhánh con trừ điểm của node đang xét. Greedy ưu tiên `h(n)` nhỏ nhất, sau đó độ sâu nhỏ hơn và thứ tự thêm vào hàng đợi.
- **Đường đi lời giải**: các phép xoay được truy ngược từ đích về trạng thái ban đầu. Click một dòng để đến bước đó. Đây là đường đi AI tìm được, có thể bỏ qua nhiều nhánh đã xét trong quá trình tìm kiếm.

Khi hai node được mở rộng liên tiếp thuộc hai nhánh khác nhau, viền vàng vẫn thể hiện phép xoay từ **cha thực sự** của node đang xem. Các chỉ số “Tại bước này” lấy từ bản ghi tương ứng; dòng “Tổng” là kết quả của toàn bộ lần chạy, không nội suy theo hoạt ảnh.

Greedy chạy trong luồng nền nên có thể xem bản ghi ngay khi tìm kiếm còn chạy. Để giới hạn bộ nhớ, UI lưu tối đa **2.000 lượt mở rộng đầu tiên và trạng thái đích nếu tìm thấy sau đó**; giao diện thông báo khi vượt giới hạn này. Việc tìm kiếm vẫn tiếp tục và đường đi lời giải giữ đầy đủ các phép xoay. Benchmark không bật ghi bản truy vết.

Chạy kiểm tra tự động (bao gồm UI với màn hình giả lập):

```powershell
python -B -m unittest discover -s tests -v
```

## Random puzzles

Every launch, size change, or press of `N` creates a new random seed and layout. The generator builds a connected network with branches and loops from a fixed source in the center, then scrambles a bounded number of tiles. Sparse mode keeps every cell occupied by a pipe, omits loops, and chooses rotations that break the most existing connections. It changes about a third of the tiles (at least four on small boards), leaving fewer matching connections at the start without adding empty cells. Press `M` to switch between Sparse and Dense. The source is the only fixed tile; every other non-cross tile can rotate. Cross pipes are skipped because rotating them does not change their connections.

Each scramble starts from a valid solution, so Greedy Best-First Search always has a solution path.

## Heuristic

`h(n)` bằng số cặp kết nối không khớp cộng thêm phạt cho số ô chưa nối được về nguồn. Trạng thái đích phải vừa không còn mismatch vừa tạo thành một mạng liên thông từ nguồn. Greedy Best-First luôn mở rộng trạng thái có `h(n)` thấp nhất trước; thuật toán ưu tiên tốc độ tìm lời giải và không đảm bảo số bước tối ưu.
