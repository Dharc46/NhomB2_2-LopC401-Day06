# Kịch bản demo 4 luồng VinDine Concierge

Tài liệu này dùng để thuyết trình hoặc demo trực tiếp 4 luồng chính đã được kiểm thử trong `tests/test_4_paths.py`: Happy Path, Low-confidence, Failure và Correction.

## Mở đầu

Xin chào mọi người. Đây là VinDine Concierge, một trợ lý AI hỗ trợ khách trong khu nghỉ dưỡng chọn nhà hàng phù hợp với nhu cầu của cả nhóm.

Điểm quan trọng của ứng dụng là AI không tự động quyết định thay người dùng. AI sẽ đọc nhu cầu bằng ngôn ngữ tự nhiên, tách thành các tiêu chí như số người, vị trí, voucher, món ăn, trẻ em, người lớn tuổi, xe đẩy, ngân sách và độ yên tĩnh. Sau đó hệ thống lọc, xếp hạng và giải thích vì sao đề xuất từng nhà hàng.

Trong phần demo này, tôi sẽ trình bày 4 tình huống chính.

## Luồng 1: Happy Path

### Mục tiêu

Chứng minh hệ thống hiểu được một yêu cầu đầy đủ, phân loại được ràng buộc cứng và sở thích mềm, rồi trả về danh sách gợi ý phù hợp.

### Câu nhập demo

```text
Nhom 6 nguoi o sanh chinh, co voucher buffet, ong ba muon mon Viet, tre con thich pizza, can xe day
```

### Lời thuyết trình

Ở luồng đầu tiên, người dùng cung cấp khá đầy đủ thông tin: nhóm có 6 người, đang ở sảnh chính, có voucher buffet, có ông bà, có trẻ em, muốn món Việt hoặc pizza và cần xe đẩy.

Hệ thống sẽ parse câu này thành các tiêu chí có cấu trúc. Một số tiêu chí được xem là ràng buộc cứng, ví dụ cần dùng voucher và cần hỗ trợ xe đẩy. Một số tiêu chí khác là sở thích mềm, ví dụ món Việt, pizza, phù hợp cho trẻ em và người lớn tuổi.

Sau đó backend sẽ lọc các nhà hàng không đáp ứng điều kiện cứng, rồi xếp hạng các nhà hàng còn lại bằng điểm phù hợp. Kết quả mong đợi là trạng thái `success` và có danh sách đề xuất.

### Điều cần chỉ ra trên màn hình

* Trạng thái trả về là `success`.
* Có Top 3 nhà hàng được đề xuất.
* Phần tiêu chí đã trích xuất có `party_size = 6`.
* Có `voucher_required = true`.
* Có `has_kids = true`, `has_elderly = true`, `needs_stroller = true`.
* Mỗi card có điểm phù hợp, lý do chọn và trade-off nếu có.

## Luồng 2: Low-confidence

### Mục tiêu

Chứng minh hệ thống không đoán bừa khi thông tin còn thiếu, mà chuyển sang hỏi làm rõ.

### Câu nhập demo

```text
Tim quan an ngon co voucher
```

### Lời thuyết trình

Ở tình huống thứ hai, người dùng chỉ nói muốn tìm quán ăn ngon có voucher. Câu này có liên quan đến ăn uống, nhưng còn thiếu nhiều thông tin quan trọng: người dùng đang ở đâu, voucher là loại nào, ngân sách bao nhiêu, đi với ai và có yêu cầu đặc biệt không.

Thay vì trả ngay một danh sách có độ tin cậy thấp, hệ thống nhận diện đây là trường hợp thiếu thông tin. Parser vẫn trích xuất được ý định có voucher, nhưng confidence thấp. Vì vậy ứng dụng sẽ hỏi thêm các câu làm rõ.

### Điều cần chỉ ra trên màn hình

* Trạng thái có thể là `needs_clarification`.
* Ứng dụng hiển thị câu hỏi làm rõ.
* Hai câu hỏi quan trọng thường là:
  * Người dùng đang ở khu hoặc sảnh nào?
  * Voucher là loại nào?
* Đây là cơ chế giảm rủi ro đề xuất sai.

## Luồng 3: Failure / No Match

### Mục tiêu

Chứng minh hệ thống xử lý được yêu cầu mâu thuẫn hoặc quá chặt, và đưa ra phương án phục hồi.

### Câu nhập demo

```text
Tim mon duoi 40k moi nguoi trong resort, co voucher buffet
```

### Lời thuyết trình

Ở tình huống thứ ba, người dùng yêu cầu món dưới 40 nghìn một người trong resort và phải có voucher buffet. Đây là yêu cầu rất khó vì ngân sách quá thấp so với dữ liệu nhà hàng trong resort, đồng thời còn bị giới hạn bởi voucher buffet.

Hệ thống sẽ phân loại ngân sách và voucher là ràng buộc cứng. Sau khi lọc, nếu không còn nhà hàng phù hợp, hệ thống không tạo đề xuất giả. Thay vào đó, nó trả về trạng thái `no_match` và đưa ra các lựa chọn phục hồi.

### Điều cần chỉ ra trên màn hình

* Trạng thái trả về là `no_match`.
* Danh sách recommendation rỗng.
* Có `fallback_suggestions`.
* Error route có hành động tiếp theo là `relax_constraint`.
* Có thể giải thích rằng hệ thống đề xuất nới ngân sách, đổi loại voucher hoặc mở rộng phạm vi tìm kiếm.

## Luồng 4: Correction / Re-rank

### Mục tiêu

Chứng minh người dùng có thể phản hồi sau kết quả đầu tiên, và hệ thống sẽ hiểu correction để xếp hạng lại.

### Câu nhập demo lần đầu

```text
Nhom 4 nguoi o food court, muon an nhe gan nhat
```

### Câu correction

```text
Quan nay on ao, ong ba khong thich. Can cho yen tinh hon.
```

### Lời thuyết trình

Ở tình huống cuối cùng, người dùng ban đầu chỉ yêu cầu nhóm 4 người ở food court, muốn ăn nhẹ và gần nhất. Hệ thống sẽ trả về đề xuất ban đầu dựa trên vị trí và nhu cầu ăn nhẹ.

Sau đó người dùng phản hồi rằng quán này ồn ào, ông bà không thích, cần chỗ yên tĩnh hơn. Đây là correction. Hệ thống sẽ parse lại thông tin mới, nhận ra có người lớn tuổi và có sở thích yên tĩnh. Từ đó ranking engine điều chỉnh trọng số, ưu tiên các nhà hàng yên tĩnh và phù hợp hơn cho người lớn tuổi.

### Điều cần chỉ ra trên màn hình

* Kết quả sau correction vẫn có recommendation.
* `quiet_preferred = true`.
* `has_elderly = true`.
* Top recommendation có thể thay đổi hoặc điểm phù hợp thay đổi.
* Đây là ví dụ cho vai trò “human-in-the-loop”: người dùng phản hồi, AI học tín hiệu trong phiên và xếp hạng lại.

## Kết luận demo

Qua 4 luồng này, VinDine Concierge thể hiện được các năng lực chính:

* Hiểu yêu cầu ăn uống tự nhiên của người dùng.
* Phân biệt ràng buộc cứng và sở thích mềm.
* Không đoán bừa khi thiếu thông tin.
* Không tạo kết quả giả khi không có nhà hàng phù hợp.
* Cho phép người dùng sửa hướng và xếp hạng lại.
* Giải thích đề xuất theo nhiều tiêu chí, không chỉ dựa vào rating.

Thông điệp chính là: VinDine Concierge không thay người dùng quyết định, mà giúp nhóm ra quyết định nhanh hơn, rõ ràng hơn và ít rủi ro hơn.
