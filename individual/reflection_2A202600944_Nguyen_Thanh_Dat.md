# Bảng nhiệm vụ cá nhân – dharc46

## Dự án: VinDine Concierge

Dựa trên vai trò **“Người 1 — Data + Glue”**, phần nhiệm vụ cá nhân của tôi trong nhóm có thể được mô tả như sau:

## Bảng tổng quan vai trò

| Thành viên | Vai trò chính | Việc phụ trách |
|---|---|---|
| **dharc46** | **Data + Glue / Integration & Demo Support** | Chuẩn hóa dữ liệu nhà hàng, tích hợp các phần backend – parser – ranking thành một luồng API thống nhất, hỗ trợ kiểm thử prototype, xử lý Git/version control và chuẩn bị demo sản phẩm. |

## Bảng nhiệm vụ chi tiết

| Nhóm việc | Nhiệm vụ cụ thể | Kết quả đóng góp |
|---|---|---|
| **Data & Schema** | Đẩy JSON schema sớm để nhóm thống nhất cấu trúc dữ liệu nhà hàng. | Giúp các phần parser, ranking và API dùng chung một format dữ liệu. |
| **Mock Restaurant Data** | Hỗ trợ điền dữ liệu mock cho khoảng 30–40 nhà hàng. | Prototype có đủ dữ liệu để chạy demo và kiểm thử recommendation. |
| **Backend / FastAPI** | Hỗ trợ dựng và kiểm tra các endpoint FastAPI. | Backend có API phục vụ cho luồng tìm kiếm và gợi ý nhà hàng. |
| **Glue Logic** | Kết nối parser và ranking vào một API duy nhất. | Người dùng nhập nhu cầu, hệ thống có thể phân tích yêu cầu và trả về gợi ý nhà hàng phù hợp. |
| **Version Control** | Merge branch, xử lý conflict ở các file như `src/app.py`, `src/api.py`, `tests/test_api.py`. | Giữ code của nhóm đồng bộ, tránh mất tính năng hoặc lỗi trước demo. |
| **UI Demo** | Cập nhật giao diện Streamlit, thêm background nội bộ, xóa phần UI không cần thiết, kiểm tra lỗi hiển thị. | Prototype nhìn hoàn chỉnh hơn và dễ trình bày trong demo. |
| **Testing AI Flow** | Kiểm tra các luồng như happy path, low-confidence, no match, correction/re-rank và off-topic. | Phát hiện lỗi chatbot trả lời sai phạm vi, giúp nhóm cải thiện fallback và routing. |
| **API Key & Environment** | Kiểm tra Gemini API key, file `.env`, lỗi provider và lỗi môi trường. | Giúp phân biệt lỗi do key, repo version hay logic xử lý. |
| **Documentation / Evidence Pack** | Viết tài liệu demo tiếng Việt, chuẩn hóa 4 luồng test chính và phần reflection cá nhân. | Nhóm có kịch bản demo rõ ràng và evidence pack đầy đủ hơn. |

## Mô tả ngắn để đưa vào báo cáo

Trong nhóm, tôi đảm nhiệm vai trò **Data + Glue**, tức là người hỗ trợ chuẩn hóa dữ liệu, kết nối các thành phần kỹ thuật và đảm bảo prototype có thể chạy được như một sản phẩm hoàn chỉnh. Tôi không chỉ làm một module riêng lẻ, mà còn hỗ trợ nối backend, parser, ranking, UI, test và tài liệu demo thành một luồng thống nhất.

Đóng góp chính của tôi là giúp **VinDine Concierge** trở thành một prototype có thể chạy, kiểm thử, merge và trình bày được trong buổi demo. Công việc của tôi tập trung vào việc đảm bảo AI không hoạt động như một chatbot tự do, mà hỗ trợ đúng mục tiêu sản phẩm: giúp khách Vinpearl/VinWonders chọn nhà hàng phù hợp hơn dựa trên nhu cầu của nhóm.

## Tóm tắt đóng góp chính

- Chuẩn hóa dữ liệu và JSON schema cho nhà hàng.
- Hỗ trợ tạo dữ liệu mock cho 30–40 nhà hàng.
- Kết nối parser và ranking vào một API duy nhất.
- Hỗ trợ dựng và kiểm tra FastAPI endpoints.
- Quản lý merge branch, xử lý conflict và đồng bộ repo.
- Cải thiện giao diện Streamlit để phục vụ demo.
- Kiểm thử các luồng AI chính, bao gồm cả off-topic và correction.
- Kiểm tra Gemini API key, `.env` và lỗi môi trường.
- Viết tài liệu demo và evidence pack cho nhóm.

## Kết luận cá nhân

Qua dự án này, tôi hiểu rằng một prototype AI product tốt không chỉ cần model trả lời hay. Sản phẩm cần có SPEC rõ ràng, dữ liệu đủ tốt, parser đáng tin, fallback hợp lý, test bảo vệ các luồng chính và UI đủ dễ hiểu để người dùng tin tưởng.

Vai trò **Data + Glue** giúp tôi học được cách nhìn AI như một phần trong workflow sản phẩm, không phải toàn bộ sản phẩm. Đóng góp lớn nhất của tôi là giúp prototype trở thành một phiên bản có thể chạy, kiểm thử, merge và demo được.
