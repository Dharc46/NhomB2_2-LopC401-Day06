# SPEC sản phẩm

> Ở Day 5, các nhóm đã nộp một bản **SPEC nhẹ (light spec)**. Day 6 chỉ hoàn thiện bản này cho đủ để build và demo — vẫn gọn, **không cần tài liệu dài**.

Viết SPEC vào `spec/spec.md`. Có thể kèm slide demo (`spec/demo-slides.pdf`) nếu có.

---

## SPEC gồm các phần sau

### 1. Bằng chứng (Evidence)
Nhóm thấy nỗi đau thật ở đâu? Từ nguồn nào — tự trải nghiệm app, review công khai, phỏng vấn nhanh, hay đối thủ? Kèm quote / screenshot.
> Không có nguồn ngoài nhóm → đánh dấu rõ là **giả định**.

### 2. Lát cắt build (Build slice)
Một người dùng · một việc · một quyết định của AI · một đầu ra. Lát cắt nhỏ nhất chứng minh được ý tưởng.

### 3. AI Product Canvas
- **Value** — cho ai, đau ở đâu, AI giải được gì mà cách hiện tại chưa giải tốt?
- **Trust** — khi AI sai thì sao? Người dùng biết, sửa, hoàn tác, hay chuyển người thật bằng cách nào?
- **Feasibility** — có đáng build không? Chi phí / độ trễ / dữ liệu / rủi ro chính.
- **Learning signal** — phần người dùng sửa đi về đâu, sản phẩm tốt lên nhờ tín hiệu nào?

### 4. Augment hay Automate
AI gợi ý, chuẩn bị, hay tự hành động? Con người giữ quyền quyết định ở bước nào?

### 5. Bốn đường đi (User Stories)

| Đường đi | Câu hỏi phải trả lời |
|----------|----------------------|
| Đường thuận | AI đúng và tự tin — người dùng thấy gì? |
| Khi AI không chắc | Có hỏi lại / đưa vài lựa chọn không? |
| Khi AI sai | Người dùng phục hồi thế nào? |
| Khi người dùng sửa | Phần sửa đó đi về đâu? |

### 6. Top failure modes
Kiểu lỗi nguy hiểm nhất là gì? Khi nào kích hoạt, hậu quả ra sao, và prototype xử lý bằng cách nào?

### 7. Owner plan (phân công)
Ai làm prompt / test, ai làm giao diện, ai giữ repo, ai viết kịch bản demo, ai lo bằng chứng?

---

*Day 6 không cần ROI nhiều kịch bản, không cần công thức eval — phần đó để dành cho giai đoạn chuyên sâu. Hôm nay tập trung: **bằng chứng → lát cắt → demo chạy được**.*
