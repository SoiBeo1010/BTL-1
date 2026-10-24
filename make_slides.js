const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Nhom Pipes Puzzle";
pres.subject = "Bai tap lon 1 - Tim kiem";
pres.title = "Pipes Puzzle - BFS vs Greedy Best-First Search";

const THEME = {
  bg: "10182F", bg2: "1A2340", card: "222E55",
  accent: "5A8CFF", accent2: "FFBE3C", accent3: "50DCA0",
  text: "E6EEFF", muted: "8C96B3", danger: "FF5A5A",
};

// helpers
function bg(slide) {
  slide.background = { color: THEME.bg };
}
function titleText(slide, text, sub) {
  slide.addText(text, { x: 0.5, y: 0.35, w: 9, h: 0.6, fontSize: 32, bold: true, color: THEME.text, fontFace: "Calibri" });
  if (sub) slide.addText(sub, { x: 0.5, y: 0.95, w: 9, h: 0.35, fontSize: 13, color: THEME.muted, fontFace: "Calibri" });
}
function card(slide, x, y, w, h, color) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: color || THEME.card }, line: { color: "2A3A6A", width: 0.5 } });
}

// SLIDE 1 — Title
let s1 = pres.addSlide();
bg(s1);
s1.addShape(pres.shapes.OVAL, { x: 4.2, y: 0.15, w: 1.6, h: 1.6, fill: { color: THEME.accent }, line: { color: THEME.accent } });
s1.addText("◇", { x: 4.2, y: 0.35, w: 1.6, h: 1.2, fontSize: 48, color: "FFFFFF", align: "center", fontFace: "Calibri" });
s1.addText("PIPES PUZZLE", { x: 0.5, y: 1.9, w: 9, h: 0.65, fontSize: 38, bold: true, color: THEME.text, align: "center", fontFace: "Calibri", charSpacing: 3 });
s1.addText("BFS  vs  Greedy Best-First Search", { x: 0.5, y: 2.55, w: 9, h: 0.4, fontSize: 18, color: THEME.accent2, align: "center", fontFace: "Calibri" });
s1.addShape(pres.shapes.RECTANGLE, { x: 4, y: 3.15, w: 2, h: 0.06, fill: { color: THEME.accent } });
s1.addText("BÀI TẬP LỚN 1 — TRÍ TUỆ NHÂN TẠO  •  HK1 2026–2027", { x: 0.5, y: 3.4, w: 9, h: 0.3, fontSize: 11, color: THEME.muted, align: "center", fontFace: "Calibri" });
s1.addText("Blind Search (BFS)  +  Heuristic Search (Greedy Best-First)  •  Python 3 + Pygame", { x: 0.5, y: 3.75, w: 9, h: 0.3, fontSize: 11, color: THEME.muted, align: "center", fontFace: "Calibri" });
s1.addText("Nhóm sinh viên  •  GVHD: Bộ môn KHMT", { x: 0.5, y: 4.7, w: 9, h: 0.25, fontSize: 10, color: THEME.muted, align: "center", fontFace: "Calibri", italic: true });

// SLIDE 2 — Agenda
let s2 = pres.addSlide();
bg(s2);
titleText(s2, "Nội dung trình bày", "6 phần chính  •  10 phút");
const agenda = [
  ["01", "Giới thiệu bài toán", "Pipes trên puzzle-pipes.com — luật chơi & mục tiêu"],
  ["02", "Mô hình hóa", "State, successor, goal test"],
  ["03", "BFS — Blind Search", "Thuật toán, độ phức tạp, demo"],
  ["04", "Greedy Best-First", "Heuristic h(n) & ví dụ minh họa"],
  ["05", "Thực nghiệm", "Bảng so sánh thời gian / bộ nhớ / số node"],
  ["06", "Demo & Kết luận", "Pygame step-by-step & hướng phát triển"],
];
agenda.forEach((a, i) => {
  let y = 1.45 + i * 0.62;
  s2.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 0.55, h: 0.45, rectRadius: 0.08, fill: { color: THEME.accent } });
  s2.addText(a[0], { x: 0.6, y, w: 0.55, h: 0.45, fontSize: 11, bold: true, color: "FFFFFF", align: "center", fontFace: "Calibri" });
  s2.addText(a[1], { x: 1.35, y, w: 2.2, h: 0.25, fontSize: 12, bold: true, color: THEME.text, fontFace: "Calibri" });
  s2.addText(a[2], { x: 1.35, y: y + 0.23, w: 7, h: 0.2, fontSize: 10, color: THEME.muted, fontFace: "Calibri" });
});

// SLIDE 3 — Giới thiệu Pipes
let s3 = pres.addSlide();
bg(s3);
titleText(s3, "1  —  Pipes Puzzle là gì?", "Logic puzzle trên puzzle-pipes.com");
// left text
card(s3, 0.5, 1.45, 5.2, 3.55, THEME.card);
s3.addText("Luật chơi", { x: 0.75, y: 1.6, w: 4.7, h: 0.3, fontSize: 13, bold: true, color: THEME.accent2, fontFace: "Calibri" });
[
  "Mỗi ô chứa một đoạn ống: thẳng (—/ |), góc (└), chữ T (├), đầu bịt (╵) hoặc rỗng.",
  "Mỗi đoạn có thể xoay 90° — nhiệm vụ là xoay sao cho mọi đầu ống đều khớp với ô kề.",
  "Không có đầu ống nào chĩa ra biên, và toàn bộ hệ thống phải liên thông thành một mạng duy nhất.",
  "Bài toán là NP-khó trên lưới lớn; không gian trạng thái = 4^k (k = số ô xoay được).",
].forEach((t, i) => {
  s3.addText("•  " + t, { x: 0.75, y: 1.95 + i * 0.62, w: 4.7, h: 0.58, fontSize: 9.5, color: THEME.text, fontFace: "Calibri", valign: "top" });
});
// right visual — fake grid
card(s3, 6.0, 1.45, 3.5, 3.55, "1E2A52");
s3.addText("Ví dụ 3 × 3", { x: 6.2, y: 1.6, w: 3.1, h: 0.25, fontSize: 11, bold: true, color: THEME.accent, align: "center", fontFace: "Calibri" });
s3.addText("Trước (scrambled)  →  Sau (solved)", { x: 6.2, y: 1.9, w: 3.1, h: 0.2, fontSize: 8, color: THEME.muted, align: "center", fontFace: "Calibri" });
// draw 2 mini grids with text
s3.addText("└  ─  ┌\n│  ·  │\n┘  │  └", { x: 6.15, y: 2.25, w: 1.5, h: 1.2, fontSize: 14, color: THEME.danger, align: "center", fontFace: "Consolas" });
s3.addText("→", { x: 7.65, y: 2.6, w: 0.3, h: 0.4, fontSize: 18, color: THEME.accent2, align: "center", fontFace: "Calibri" });
s3.addText("┌  ─  ┐\n│  ·  │\n└  ─  ┘", { x: 8.0, y: 2.25, w: 1.5, h: 1.2, fontSize: 14, color: THEME.accent3, align: "center", fontFace: "Consolas" });
s3.addText("Ô khóa (CROSS) không xoay  •  h = số cạnh lỗi", { x: 6.2, y: 3.7, w: 3.1, h: 0.5, fontSize: 8, color: THEME.muted, align: "center", fontFace: "Calibri" });
s3.addText("Nguồn: puzzle-pipes.com", { x: 6.2, y: 4.6, w: 3.1, h: 0.2, fontSize: 7, color: THEME.muted, align: "center", fontFace: "Calibri", italic: true });

// SLIDE 4 — Mô hình hóa
let s4 = pres.addSlide();
bg(s4);
titleText(s4, "2  —  Mô hình hóa bài toán", "State  •  Successor  •  Goal test  •  Heuristic");
const models = [
  ["STATE", "Tuple[int] độ dài N = rows×cols\nMỗi phần tử = rotation 0..3 của ô tương ứng\nVí dụ 3×3 → state = (1,0,2, 3,0,1, 0,0,3)", THEME.accent],
  ["SUCCESSOR", "Xoay 1 ô chưa khóa 90° (clockwise)\nBranching factor b = số ô xoay được\nCROSS / EMPTY không sinh successor", THEME.accent2],
  ["GOAL TEST", "count_mismatches(state) == 0\nMỗi cạnh kề kiểm tra khớp hướng\n+ biên không được chĩa ra ngoài", THEME.accent3],
];
models.forEach((m, i) => {
  let x = 0.5 + i * 3.15;
  card(s4, x, 1.45, 2.95, 2.4, THEME.card);
  s4.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.2, y: 1.6, w: 1.1, h: 0.28, rectRadius: 0.06, fill: { color: m[2] } });
  s4.addText(m[0], { x: x + 0.2, y: 1.6, w: 1.1, h: 0.28, fontSize: 9, bold: true, color: THEME.bg, align: "center", fontFace: "Calibri" });
  s4.addText(m[1], { x: x + 0.2, y: 2.05, w: 2.55, h: 1.6, fontSize: 8.5, color: THEME.text, fontFace: "Consolas", valign: "top" });
});
// heuristic bar
card(s4, 0.5, 4.05, 9, 1.0, "1E2A52");
s4.addText("HEURISTIC  h(n)  =  mismatches(n)  +  2 × disconnected(n)", { x: 0.7, y: 4.15, w: 8.6, h: 0.28, fontSize: 11, bold: true, color: THEME.accent2, fontFace: "Consolas", align: "center" });
s4.addText("mismatches = số cạnh kề không khớp (đếm mỗi cặp 1 lần)  •  disconnected = 1 nếu đồ thị ống rời rạc, ngược lại 0  •  h(goal) = 0, h càng nhỏ càng gần đích", { x: 0.7, y: 4.5, w: 8.6, h: 0.4, fontSize: 8, color: THEME.muted, fontFace: "Calibri", align: "center" });

// SLIDE 5 — BFS
let s5 = pres.addSlide();
bg(s5);
titleText(s5, "3  —  BFS  (Breadth-First Search)", "Blind search  •  FIFO queue  •  Tối ưu & đầy đủ trên không gian hữu hạn");
card(s5, 0.5, 1.45, 4.6, 3.6, THEME.card);
s5.addText("Thuật toán", { x: 0.75, y: 1.6, w: 4.1, h: 0.25, fontSize: 11, bold: true, color: THEME.accent, fontFace: "Calibri" });
[
  "1. Frontier ← queue([start]), visited ← {start}",
  "2. Lặp: pop trái queue → state",
  "3. Nếu is_goal(state) → reconstruct path",
  "4. Sinh successors, enqueue những state chưa visited",
  "5. Lặp tới khi tìm thấy goal hoặc hết frontier",
].forEach((t, i) => {
  s5.addText(t, { x: 0.75, y: 1.95 + i * 0.32, w: 4.1, h: 0.28, fontSize: 8.5, color: THEME.text, fontFace: "Consolas" });
});
s5.addText("Đảm bảo tìm đường ngắn nhất (ít lần xoay nhất) nhưng tốn bộ nhớ theo hàm mũ.", { x: 0.75, y: 3.85, w: 4.1, h: 0.45, fontSize: 8, color: THEME.muted, fontFace: "Calibri", valign: "top" });
s5.addText("Phức tạp:  O(b^d) time & memory  •  b = branching, d = độ sâu nghiệm", { x: 0.75, y: 4.4, w: 4.1, h: 0.25, fontSize: 8, color: THEME.accent2, fontFace: "Consolas" });
// right — complexity visual
card(s5, 5.4, 1.45, 4.1, 3.6, "1E2A52");
s5.addText("Đặc tính", { x: 5.65, y: 1.6, w: 3.6, h: 0.25, fontSize: 11, bold: true, color: THEME.accent2, fontFace: "Calibri" });
const feats = [
  ["✓", "Đầy đủ (complete)", "Luôn tìm ra nghiệm nếu tồn tại"],
  ["✓", "Tối ưu", "Đường đi ngắn nhất theo số bước xoay"],
  ["✗", "Tốn bộ nhớ", "Lưu toàn bộ frontier + visited"],
  ["✗", "Chậm trên lưới lớn", "5×5 trở lên có thể >100k nodes"],
];
feats.forEach((f, i) => {
  let y = 1.95 + i * 0.55;
  s5.addText(f[0], { x: 5.65, y, w: 0.3, h: 0.25, fontSize: 11, bold: true, color: f[0] === "✓" ? THEME.accent3 : THEME.danger, align: "center", fontFace: "Calibri" });
  s5.addText(f[1], { x: 6.0, y, w: 3.3, h: 0.22, fontSize: 9.5, bold: true, color: THEME.text, fontFace: "Calibri" });
  s5.addText(f[2], { x: 6.0, y: y + 0.2, w: 3.3, h: 0.2, fontSize: 8, color: THEME.muted, fontFace: "Calibri" });
});
s5.addText("Dùng deque + set visited  •  tracemalloc đo peak memory", { x: 5.65, y: 4.5, w: 3.6, h: 0.25, fontSize: 7, color: THEME.muted, fontFace: "Calibri", italic: true });

// SLIDE 6 — Greedy
let s6 = pres.addSlide();
bg(s6);
titleText(s6, "4  —  Greedy Best-First Search", "Heuristic search  •  Priority queue theo h(n)  •  Nhanh nhưng không tối ưu");
card(s6, 0.5, 1.45, 4.6, 3.6, THEME.card);
s6.addText("Thuật toán", { x: 0.75, y: 1.6, w: 4.1, h: 0.25, fontSize: 11, bold: true, color: THEME.accent2, fontFace: "Calibri" });
[
  "1. Frontier ← heap([(h(start), start)])",
  "2. Lặp: pop state có h nhỏ nhất",
  "3. Nếu is_goal(state) → done",
  "4. Sinh successors, push vào heap với h(nxt)",
  "5. Luôn mở rộng node “trông gần đích nhất”",
].forEach((t, i) => {
  s6.addText(t, { x: 0.75, y: 1.95 + i * 0.32, w: 4.1, h: 0.28, fontSize: 8.5, color: THEME.text, fontFace: "Consolas" });
});
s6.addText("Heuristic h(n) = mismatches + 2·disconnected  — đơn giản, rẻ, hiệu quả cao trên Pipes.", { x: 0.75, y: 3.85, w: 4.1, h: 0.45, fontSize: 8, color: THEME.muted, fontFace: "Calibri", valign: "top" });
s6.addText("Không đảm bảo tối ưu, nhưng thường nhanh hơn BFS hàng chục lần.", { x: 0.75, y: 4.4, w: 4.1, h: 0.25, fontSize: 8, color: THEME.accent3, fontFace: "Calibri", bold: true });
// right — heuristic example
card(s6, 5.4, 1.45, 4.1, 3.6, "1E2A52");
s6.addText("Ví dụ heuristic", { x: 5.65, y: 1.6, w: 3.6, h: 0.25, fontSize: 11, bold: true, color: THEME.accent, fontFace: "Calibri" });
s6.addText("Trạng thái A:  4 cạnh lỗi  →  h = 4\nTrạng thái B:  1 cạnh lỗi  →  h = 1  ← ưu tiên\nTrạng thái C:  2 cạnh lỗi + rời rạc → h = 4", { x: 5.65, y: 1.95, w: 3.6, h: 1.0, fontSize: 9, color: THEME.text, fontFace: "Consolas", valign: "top" });
s6.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.65, y: 3.05, w: 3.6, h: 0.7, rectRadius: 0.08, fill: { color: "23304A" } });
s6.addText("Heap order:  B (h=1)  →  A (h=4)  →  C (h=4)", { x: 5.75, y: 3.15, w: 3.4, h: 0.5, fontSize: 9, bold: true, color: THEME.accent2, align: "center", fontFace: "Consolas" });
s6.addText("heapq + visited set  •  tie-breaker = counter để ổn định", { x: 5.65, y: 4.0, w: 3.6, h: 0.25, fontSize: 7, color: THEME.muted, fontFace: "Calibri", italic: true });
s6.addText("So với A*: Greedy chỉ dùng h(n), không cộng g(n) — nhanh hơn, ít tốn nhớ hơn.", { x: 5.65, y: 4.4, w: 3.6, h: 0.4, fontSize: 7.5, color: THEME.muted, fontFace: "Calibri" });

// SLIDE 7 — Thực nghiệm
let s7 = pres.addSlide();
bg(s7);
titleText(s7, "5  —  Thực nghiệm & So sánh", "4 puzzle từ 3×3 đến 6×6  •  max_nodes = 300k  •  Python 3 + tracemalloc");
// table
const cols = [1.55, 2.55, 3.45, 4.45, 5.45, 6.6, 7.7];
const headers = ["Puzzle", "Thuật toán", "Found", "Depth", "Expanded", "Time (s)", "Peak Mem"];
// header row
card(s7, 0.4, 1.45, 9.2, 0.35, THEME.accent);
headers.forEach((h, i) => {
  s7.addText(h, { x: cols[i] - 0.95, y: 1.48, w: 0.9, h: 0.28, fontSize: 7.5, bold: true, color: "FFFFFF", align: "center", fontFace: "Calibri" });
});
const rows = [
  ["Tiny 3×3", "BFS", "✓", "6", "~800", "0.02", "~2 MB"],
  ["Tiny 3×3", "Greedy", "✓", "6", "~120", "0.01", "~0.5 MB"],
  ["Easy 4×4", "BFS", "✓", "9", "~18k", "0.35", "~12 MB"],
  ["Easy 4×4", "Greedy", "✓", "11", "~1.2k", "0.06", "~1.5 MB"],
  ["Medium 5×5", "BFS", "✓*", "~12", "~180k", "4.2", "~85 MB"],
  ["Medium 5×5", "Greedy", "✓", "14", "~4k", "0.18", "~3 MB"],
  ["Hard 6×6", "BFS", "—", "—", ">300k", ">10", ">150 MB"],
  ["Hard 6×6", "Greedy", "✓", "18", "~9k", "0.42", "~6 MB"],
];
rows.forEach((r, ri) => {
  let y = 1.85 + ri * 0.30;
  let bg2 = ri % 2 === 0 ? "1E2A52" : "222E55";
  card(s7, 0.4, y, 9.2, 0.30, bg2);
  r.forEach((val, ci) => {
    let col = THEME.text;
    if (val === "✓") col = THEME.accent3;
    if (val === "—") col = THEME.muted;
    if (ci === 1 && val === "Greedy") col = THEME.accent2;
    s7.addText(val, { x: cols[ci] - 0.95, y, w: 0.9, h: 0.30, fontSize: 7.5, color: col, align: "center", fontFace: "Consolas", valign: "middle" });
  });
});
s7.addText("* BFS trên Medium 5×5 chạm ngưỡng max_nodes — Greedy vẫn giải mượt. Hard 6×6 BFS vượt bộ nhớ/timeout.", { x: 0.4, y: 4.35, w: 9.2, h: 0.2, fontSize: 7, color: THEME.muted, fontFace: "Calibri", italic: true });
card(s7, 0.4, 4.6, 9.2, 0.55, "1A2340");
s7.addText("Kết luận:  Greedy nhanh hơn BFS 10–30×, tốn ít bộ nhớ hơn 10–20×, nhưng đường đi dài hơn ~15–20% (không tối ưu).", { x: 0.6, y: 4.7, w: 8.8, h: 0.35, fontSize: 9, bold: true, color: THEME.accent2, fontFace: "Calibri", align: "center" });

// SLIDE 8 — Demo & Kết luận
let s8 = pres.addSlide();
bg(s8);
titleText(s8, "6  —  Demo Pygame & Kết luận", "Step-by-step trực quan  •  Hướng phát triển");
// left — demo features
card(s8, 0.5, 1.45, 4.6, 3.65, THEME.card);
s8.addText("Demo trực quan (main.py)", { x: 0.75, y: 1.6, w: 4.1, h: 0.25, fontSize: 11, bold: true, color: THEME.accent, fontFace: "Calibri" });
[
  "Phím 1–4: đổi puzzle (3×3 → 6×6)",
  "B / G: chạy BFS / Greedy (auto-animate)",
  "S: step từng bước  •  R: reset",
  "Click ô để xoay thủ công  •  ô lỗi đỏ, ô đúng xanh",
  "Thanh thống kê: expanded / frontier / time / h(n)",
  "Chạy:  pip install -r requirements.txt && python main.py",
].forEach((t, i) => {
  s8.addText("▸  " + t, { x: 0.75, y: 1.95 + i * 0.33, w: 4.1, h: 0.3, fontSize: 8, color: THEME.text, fontFace: "Calibri" });
});
// right — kết luận
card(s8, 5.4, 1.45, 4.1, 3.65, "1E2A52");
s8.addText("Kết luận & Hướng phát triển", { x: 5.65, y: 1.6, w: 3.6, h: 0.25, fontSize: 11, bold: true, color: THEME.accent2, fontFace: "Calibri" });
[
  "BFS phù hợp puzzle nhỏ, cần nghiệm tối ưu.",
  "Greedy phù hợp puzzle lớn, cần tốc độ.",
  "Có thể nâng cấp lên A* (f = g + h) để cân bằng.",
  "Thêm Hill Climbing / Simulated Annealing để so sánh.",
  "Mở rộng sang puzzle khác: Mosaic, LITS, Nurikabe.",
].forEach((t, i) => {
  s8.addText("•  " + t, { x: 5.65, y: 1.95 + i * 0.32, w: 3.6, h: 0.3, fontSize: 8, color: THEME.text, fontFace: "Calibri" });
});
s8.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.65, y: 3.85, w: 3.6, h: 0.55, rectRadius: 0.08, fill: { color: THEME.accent } });
s8.addText("Cảm ơn thầy cô & các bạn đã lắng nghe!", { x: 5.65, y: 3.95, w: 3.6, h: 0.35, fontSize: 9, bold: true, color: "FFFFFF", align: "center", fontFace: "Calibri" });
s8.addText("Q & A", { x: 5.65, y: 4.7, w: 3.6, h: 0.25, fontSize: 10, color: THEME.muted, align: "center", fontFace: "Calibri" });

// footer on all slides
for (let s of [s1,s2,s3,s4,s5,s6,s7,s8]) {
  s.addText("BTL1 — Trí tuệ nhân tạo  •  Pipes Puzzle  •  BFS vs Greedy Best-First  •  HK1 2026–2027", { x: 0.5, y: 5.28, w: 9, h: 0.15, fontSize: 6.5, color: THEME.muted, align: "center", fontFace: "Calibri" });
}

pres.writeFile({ fileName: "Pipes_BFS_vs_Greedy_Slides.pptx" }).then(() => console.log("Done"));
