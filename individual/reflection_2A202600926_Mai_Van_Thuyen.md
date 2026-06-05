# Phản ánh cá nhân (Individual Reflection)

**Họ và tên:** Mai Văn Thuyên
**Mã học viên:** 2A202600926
**Nhóm:** Nhóm B2-2 - Lớp C401  
**Vai trò trong nhóm:** Người 4 - UI + Demo

---

## 1. Công việc đã thực hiện
Trong thời gian diễn ra Hackathon (Day 05 & Day 06), tôi đã đảm nhiệm và đóng góp vào các công việc sau:
- Tích hợp và hoàn thiện giao diện người dùng (Frontend) bằng Streamlit, bao gồm việc làm mượt các luồng tương tác (Instant UI feedback, loading spinners).
- Điều chỉnh luồng 5 kịch bản (Paths) thực tế để bám sát với Thin SPEC: Happy, Low-confidence, Failure, Correction, và Off-topic.
- Cải thiện cơ chế "Click-to-select" cho thẻ nhà hàng và "Click-to-fallback", giúp giảm thao tác gõ phím của người dùng.
- Hỗ trợ xây dựng tài liệu thuyết trình (Slide Deck & SPEC).
*(Chỉnh sửa lại các gạch đầu dòng trên cho đúng với thực tế công việc bạn đã làm)*

## 2. Trải nghiệm Vibe-coding & Làm việc với AI
Trong dự án này, tôi đã áp dụng mạnh mẽ AI Tools (Antigravity/Gemini) để hỗ trợ viết code (Vibe-coding). 
- **Điểm thuận lợi:** AI giúp tốc độ ra mắt bản Prototype (Streamlit + FastAPI) tăng lên đáng kể. Đặc biệt là những công việc tốn thời gian như CSS styling, refactor luồng hiển thị (spinner, chat message) được giải quyết rất nhanh.
- **Thách thức:** AI đôi khi tự ý sửa các đoạn text tiếng Việt thành tiếng Anh hoặc làm lệch chuẩn SPEC ban đầu. 
- **Cách khắc phục:** Tôi học được rằng không thể phó mặc 100% cho AI. Bản thân tôi phải đóng vai trò là "Người điều phối" (Reviewer), đọc hiểu luồng code (`api.py`, `app.py`) để chỉ đạo AI sửa đúng luồng thay vì để nó tự quyết. Việc viết Prompt rõ ràng, nhắc nhở AI về ngữ cảnh (VD: "dùng tiếng Việt", "giữ đúng 4 paths của SPEC") là chìa khóa để Vibe-coding thành công.

## 3. Tư duy Sản phẩm (Product Thinking) & AI
- **Augment thay vì Automate:** Hệ thống VinDine chọn hướng **Augment** (hỗ trợ ra quyết định) thay vì Automate (tự động đặt bàn). Lý do là vì thông tin thực tế về quán ăn (voucher, chỗ trống, khẩu vị đặc thù) rất nhạy cảm. AI chỉ đóng vai trò phân tích, xếp hạng (Rank Top 3) và đưa ra Trade-off. Quyết định cuối cùng (Decider) phải nằm trong tay người dùng.
- **Xử lý Failure Mode:** Bài học lớn nhất của tôi là AI không được phép trả về trang trắng (No result). Khi yêu cầu quá khắt khe, hệ thống phải có "Fallback" (Ví dụ: gợi ý Kiosk, gợi ý tăng budget) dưới dạng nút bấm để "cứu vớt" luồng trải nghiệm của khách.

## 4. Bài học rút ra (Lessons Learned)
- **Tầm quan trọng của SPEC:** Codebase rất dễ bị rối và trôi xa khỏi mục tiêu nếu không có Thin SPEC làm điểm tựa. Nhờ đối chiếu lại SPEC, nhóm mới nhận ra có sự sai lệch về các luồng (Paths) và kịp thời điều chỉnh.
- **Hiểu những gì mình code:** Dù dùng AI để sinh code, việc nắm được kiến trúc hệ thống (FastAPI gọi LLM Parser thế nào, Streamlit render State ra sao) là yếu tố quyết định để xử lý lỗi và thuyết trình tự tin tại Demo Round.
- Kỹ năng làm việc nhóm và chia nhỏ công việc (Slice) trong thời gian siêu ngắn là trải nghiệm áp lực nhưng cực kỳ quý giá.

---
*Ghi chú: Bản reflection này chứng minh sự hiểu biết về codebase, luồng dữ liệu, và tư duy phát triển sản phẩm của cá nhân trong suốt Hackathon.*
