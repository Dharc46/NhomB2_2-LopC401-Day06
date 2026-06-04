# Phản ánh cá nhân - dharc46

## 1. Vai trò của tôi trong nhóm

Trong dự án VinDine Concierge, tôi tham gia với vai trò thiên về **tích hợp prototype, kiểm thử luồng sản phẩm, xử lý version control và chuẩn bị demo**. Tôi không chỉ làm một phần riêng lẻ, mà còn hỗ trợ nối các phần của nhóm lại thành một ứng dụng có thể chạy, kiểm thử và trình bày được.

Trọng tâm công việc của tôi là đảm bảo prototype thể hiện đúng ý tưởng sản phẩm: AI không thay người dùng quyết định, mà hỗ trợ khách Vinpearl/VinWonders chọn nhà hàng phù hợp hơn dựa trên nhu cầu của nhóm.

## 2. Những việc tôi đã làm

### Tích hợp và quản lý repo

Tôi phụ trách nhiều thao tác Git quan trọng trong quá trình hoàn thiện dự án:

* Merge các nhánh tính năng vào `test-branch` và `main`.
* Xử lý conflict trong các file quan trọng như `src/app.py`, `src/api.py`, `tests/test_api.py`.
* Kiểm tra trạng thái branch, commit, pull và push để đảm bảo code của nhóm không bị lệch phiên bản.
* Đảm bảo các thay đổi UI, backend, test và tài liệu được gom lại thành một phiên bản chạy được.

Việc này quan trọng vì trong hackathon, nhiều thành viên cùng sửa code rất nhanh. Nếu không quản lý merge cẩn thận, app có thể bị mất tính năng hoặc bị lỗi ngay trước demo.

### Hoàn thiện UI và trải nghiệm demo

Tôi hỗ trợ cập nhật giao diện Streamlit để app dễ trình bày hơn:

* Thêm `background.png` làm ảnh nền toàn màn hình.
* Đảm bảo ảnh nền được load từ asset nội bộ, không phụ thuộc URL bên ngoài.
* Giữ các thành phần UI nằm phía trên background và không làm hỏng chức năng chat.
* Xóa phần UI không cần thiết: “Danh sách việc cần lưu ý/xác nhận”.
* Kiểm tra lỗi hiển thị và lỗi encoding trên Windows.

Những thay đổi này giúp prototype nhìn giống một sản phẩm demo hơn, thay vì chỉ là một API hoặc giao diện thử nghiệm.

### Kiểm tra AI flow và hành vi chatbot

Tôi kiểm tra các tình huống người dùng nhập câu không liên quan như:

* `hi`
* `gió hôm nay to quá`

Ban đầu app vẫn trả về gợi ý nhà hàng trong các trường hợp này. Đây là một lỗi sản phẩm nghiêm trọng vì AI đang “cố trả lời” thay vì hiểu đúng phạm vi nhiệm vụ. Sau đó nhóm đã điều chỉnh luồng off-topic để app trả lời rằng nó chỉ hỗ trợ tìm quán ăn trong resort.

Tôi cũng kiểm tra việc dùng Gemini API key, cách cấu hình `.env`, và cách xác nhận API thật sự hoạt động. Điều này giúp phân biệt lỗi do API key, lỗi do phiên bản repo, và lỗi do logic parser.

### Viết và chuẩn hóa tài liệu demo

Tôi tạo thêm tài liệu tiếng Việt để showcase 4 luồng chính giống `test_4_paths.py`:

* Happy Path
* Low-confidence
* Failure / No Match
* Correction / Re-rank

Tài liệu này giúp nhóm có kịch bản demo rõ ràng, không chỉ chạy app ngẫu nhiên. Mỗi luồng đều có câu nhập mẫu, mục tiêu demo, lời thuyết trình và điểm cần chỉ ra trên màn hình.

## 3. Phần AI đã hỗ trợ tôi

AI hỗ trợ tôi chủ yếu ở vai trò **coding assistant và reviewer**:

* Đọc nhanh cấu trúc repo và xác định file liên quan.
* Hỗ trợ phân tích conflict khi merge branch.
* Gợi ý cách sửa lỗi runtime như UnicodeEncodeError trên Windows.
* Hỗ trợ viết tài liệu demo và reflection có cấu trúc.
* Hỗ trợ kiểm tra vì sao chatbot trả lời sai khi gặp câu off-topic.
* Hỗ trợ xác định cách cấu hình Gemini API key và biến môi trường.

Tuy nhiên, tôi vẫn phải là người quyết định cuối cùng: chọn giữ phiên bản nào khi merge, kiểm tra app có chạy không, đọc kết quả test, và xác nhận logic có đúng với mục tiêu sản phẩm không.

## 4. Những gì tôi học được

### SPEC phải đủ rõ để code không bị lệch

Trước khi làm prototype, nhóm cần thống nhất rõ AI sẽ làm gì và không làm gì. Ví dụ: VinDine Concierge chỉ hỗ trợ chọn nhà hàng, không phải chatbot nói chuyện tự do. Nếu SPEC không ghi rõ phạm vi này, chatbot dễ trả lời sai với các câu off-topic.

### AI product không chỉ là gọi API

Ban đầu tôi nghĩ phần AI quan trọng nhất là có Gemini hoặc LLM trả lời được. Sau khi làm dự án, tôi thấy phần quan trọng hơn là **routing, fallback, clarification và correction**. Một app AI tốt phải biết khi nào nên trả lời, khi nào nên hỏi thêm, và khi nào nên từ chối.

### Test giúp bảo vệ luồng sản phẩm

`test_4_paths.py` rất hữu ích vì nó không chỉ test function nhỏ, mà test cả hành vi sản phẩm:

* Câu đầy đủ phải ra recommendation.
* Câu thiếu thông tin phải hỏi lại.
* Câu quá chặt phải trả fallback.
* Câu correction phải làm thay đổi ranking.

Nhờ có test, nhóm dễ phát hiện merge nào làm hỏng logic cũ.

### Version control là một phần của sản phẩm

Trong hackathon, nhiều lỗi không đến từ thuật toán mà đến từ việc branch khác nhau, chưa pull code mới, hoặc merge conflict sai. Tôi học được rằng biết dùng Git tốt giúp nhóm giữ được tốc độ mà không làm mất tính năng.

## 5. Khó khăn tôi gặp

### Khác biệt giữa phiên bản của tôi và phiên bản của bạn khác

Có lúc app của tôi trả recommendation cho câu `hi`, trong khi phiên bản của bạn khác trả off-topic đúng hơn. Điều này khiến tôi phải kiểm tra lại branch, commit, API key và logic parser. Cuối cùng tôi hiểu rằng vấn đề không chỉ nằm ở API key, mà còn nằm ở version repo và luồng xử lý off-topic.

### Lỗi API key và provider

Gemini key có nhiều format khác nhau. Một số key bắt đầu bằng `AIzaSy`, một số key trong môi trường học có dạng khác. Tôi học được rằng app cần xử lý provider rõ ràng, không nên hardcode giả định quá hẹp về format key.

### Lỗi encoding trên Windows

Lỗi `UnicodeEncodeError` xảy ra khi app in tiếng Việt ra console Windows. Đây không phải lỗi logic AI, nhưng vẫn làm app crash. Tôi học được rằng sản phẩm demo cần xử lý cả những lỗi môi trường nhỏ như encoding, terminal và path.

## 6. Điều tôi sẽ cải thiện nếu có thêm thời gian

Nếu có thêm thời gian, tôi muốn cải thiện các phần sau:

* Thêm màn hình admin để cập nhật dữ liệu nhà hàng dễ hơn.
* Lưu correction của người dùng thành analytics rõ ràng hơn.
* Làm UI mobile gọn hơn cho tình huống khách dùng điện thoại.
* Tách frontend và backend deployment rõ ràng hơn.
* Thêm kiểm thử cho off-topic, API key failure và backend unavailable.
* Kết nối với dữ liệu thật về menu, giờ mở cửa, voucher và đặt bàn.

## 7. Kết luận cá nhân

Sau dự án này, tôi hiểu rõ hơn rằng một prototype AI product tốt không chỉ cần model trả lời hay. Nó cần có SPEC rõ, dữ liệu đủ tốt, parser đáng tin, fallback hợp lý, test bảo vệ các luồng chính và một UI đủ dễ hiểu để người dùng tin tưởng.

Đóng góp lớn nhất của tôi là giúp prototype trở thành một phiên bản có thể chạy, kiểm thử, merge và demo được. Tôi cũng học được cách nhìn AI như một phần trong workflow sản phẩm, không phải là toàn bộ sản phẩm.
