# Individual Reflection — VinDine Concierge

**Họ tên:**Nguyễn Tài Khoa
**MSSV:** 2A202600682
**Vai trò trong nhóm:** AI Integration & Architecture
**Ngày:** 04/06/2026

---

## 1. Phần mình đã làm

### Thiết kế kiến trúc AI (3-Stage Chain)

Đánh giá bản plan gốc dùng ReAct agent loop và quyết định chuyển sang kiến trúc 3-Stage Chain:

1. **Stage 1 — LLM Parser:** Dùng LLM (Gemini/Groq) parse tiếng Việt tự nhiên thành JSON cấu trúc (`ParsedConstraints`). Có off-topic guard để từ chối câu hỏi không liên quan đến ăn uống.
2. **Stage 2 — Deterministic Pipeline:** Filter cứng (voucher, budget, dietary, distance, accessibility) → ranking 8 yếu tố (100 điểm) → TF-IDF semantic menu search → geo-distance bằng haversine.
3. **Stage 3 — LLM Explainer:** Sinh giải thích tiếng Việt kiểu concierge cho từng quán được gợi ý.

**Lý do chọn Chain thay vì ReAct:** VinDine luôn chạy cùng 1 pipeline (parse → filter → rank → explain). ReAct cần 3-10 LLM calls, latency 10-20s, và kết quả không dự đoán được. Chain chỉ cần 2 LLM calls, latency 2-6s, ranking deterministic và kiểm tra được.

### Các module đã implement

| File | Mô tả |
|------|-------|
| `src/llm_client.py` | LLM client hỗ trợ Groq (free) và Google Gemini |
| `src/llm_parser.py` | Parser dùng LLM với off-topic detection |
| `src/llm_explainer.py` | Sinh giải thích tiếng Việt cho recommendations |
| `src/menu_search.py` | TF-IDF semantic menu search (lightweight RAG) |
| `src/logger.py` | Structured logging cho demo |
| `tests/test_llm.py` | 6 tests cho LLM fallback và schema validation |

### Các file đã sửa

| File | Thay đổi |
|------|----------|
| `src/preference_parser.py` | Thêm LLM-first routing, regex fallback |
| `src/api.py` | Off-topic guard, LLM explainer, logging, clarification logic |
| `src/schemas.py` | Thêm `lat`/`lng` cho Restaurant, `ai_explanations` cho Response |
| `src/ranking_engine.py` | Geo-distance (haversine), TF-IDF menu boost |
| `src/app.py` | Zone picker, AI explanations, off-topic handling, restaurant detail view |
| `data/vin_restaurants.json` | Thêm tọa độ GPS, enriched Vietnamese menu_tags cho 41 nhà hàng |

---

## 2. Cách sử dụng AI trong quá trình làm việc

### AI là công cụ, không phải tác giả

Toàn bộ quyết định kiến trúc, thiết kế, và trade-off đều do mình đưa ra thông qua thảo luận với Claude Code. AI giúp implement nhanh hơn, nhưng mọi quyết định quan trọng đều được mình review và điều chỉnh.

### Quy trình thảo luận

1. **Đánh giá plan gốc:** Mình đưa bản plan ReAct agent cho AI review. AI chỉ ra schema mismatch (field names sai so với `ParsedConstraints` thực tế), thiếu logging, và thiếu UI. Mình đồng ý và điều chỉnh.

2. **Thiết kế từng bước:** Mỗi module được thảo luận trước khi implement:
   - "Nên tạo file mới hay sửa file cũ?" → Quyết định sửa `preference_parser.py` thay vì tạo import path mới
   - "Confidence threshold nên là bao nhiêu?" → Ban đầu dùng 0.6 (magic number), mình phản biện, cuối cùng chuyển sang check `has_meaningful_constraints` (không dùng số cứng)
   - "Dùng embeddings hay TF-IDF?" → Ban đầu AI đề xuất sentence-transformers (cần PyTorch 2GB), mình abort ngay và chọn TF-IDF (0 dependencies)

3. **Phát hiện bug qua demo thực tế:** Mình test trên Streamlit UI và phát hiện:
   - "Chỉ tôi cách đảo linked list" → AI trả kết quả nhà hàng → thêm off-topic guard
   - Clarification form gửi lại original off-topic text → fix session state
   - "Chọn quán" vẫn trả recommendations dù thiếu thông tin → fix clarification logic
   - "ăn chay" bị treat như correction thay vì new query → fix correction flow logic
   - Không verify được kết quả đúng sai → thêm restaurant detail expander

4. **Quyết định provider:** Google Gemini key bị quota exhausted → thử key mới → vẫn lỗi (key format sai) → chuyển sang support cả Groq (free, OpenAI-compatible) → test thành công.

### Những lần mình không đồng ý với AI

| AI đề xuất | Mình phản biện | Kết quả |
|------------|---------------|---------|
| sentence-transformers cho embeddings | "wow why do we need that? abort" — PyTorch 2GB quá nặng cho hackathon | Chuyển sang TF-IDF, 0 dependencies, instant |
| Confidence threshold 0.6 | "isn't this too much of a magic number?" | Chuyển sang check `has_meaningful_constraints` — logic rõ ràng, không dùng số cứng |
| Tạo `streamlit_app.py` mới | "wait the UI already exists, check again" | Pull từ main, dùng `src/app.py` có sẵn |
| Ghi docs vào CLAUDE.md và README.md | "don't write to claude.md and readme.md, write into a separate spec file" | Restore file gốc, viết spec riêng trong `docs/` |
| Dump toàn bộ menu vào LLM context | "do we just add the entire menu into the llm? this is RAG right?" | Chuyển sang TF-IDF RAG pipeline đúng nghĩa |

### Những lần AI giúp mình nhìn ra vấn đề

- Schema mismatch: Plan gốc dùng `has_children` nhưng code thật dùng `has_kids` → sẽ crash khi validate
- `hard_constraints`/`soft_preferences` không nên do LLM sinh → để `classify_constraints()` deterministic xử lý
- Correction flow không cần session state → chỉ cần append correction text và re-parse

---

## 3. Kết quả kiểm thử

### Unit tests: 48/48 passed

| Test file | Số tests | Coverage |
|-----------|----------|----------|
| `test_api.py` | 8 | API endpoints, all paths |
| `test_data_loader.py` | 5 | Dataset integrity |
| `test_4_paths.py` | 4 | Happy, low-confidence, failure, correction |
| `test_ranking.py` | 25 | Filter, ranking, fallback |
| `test_llm.py` | 6 | LLM fallback, schema validation |

### E2E tests: 10 scenarios

| Scenario | Kết quả |
|----------|---------|
| Happy path (gia đình 6 người, voucher, mixed cuisine) | PASS — 9/9 checks |
| Low confidence (sparse input) | PASS — clarification form |
| Failure (impossible budget) | PASS — fallback suggestions |
| Correction (reject noisy → quiet) | PASS — re-ranked |
| Off-topic (linked list question) | PASS — polite rejection |
| Semantic search (bún bò Huế) | PASS — correct restaurant matches |
| Geo-distance (harbour zone) | PASS — walking time calculated |
| Dietary (vegetarian) | PASS — hard filter works |
| AI explanations | PASS — Vietnamese group summary |
| Simple casual query | PASS — natural input parsed |

---

## 4. Bài học rút ra

### Về AI product design

- **ReAct agent ≠ tốt nhất cho mọi bài toán.** Khi workflow cố định, deterministic chain đơn giản hơn, nhanh hơn, và dễ debug hơn.
- **Off-topic guard là bắt buộc.** Không có nó, user hỏi gì AI cũng cố trả lời → kết quả vô nghĩa.
- **Clarification > random results.** Khi thiếu thông tin, hỏi lại tốt hơn là trả kết quả 50% confidence.
- **Human-in-the-loop thật sự:** Detail view để user verify, correction flow để reject và re-rank, confidence label để user biết AI chắc đến đâu.

### Về cách dùng AI coding assistant

- **AI giỏi implement, nhưng quyết định thiết kế phải là của mình.** Mỗi lần AI đề xuất giải pháp nặng (PyTorch, dump toàn bộ data vào LLM), mình cần phản biện.
- **Test trên UI thật, không chỉ unit test.** Phần lớn bug (off-topic, correction flow, clarification showing results) chỉ phát hiện khi dùng Streamlit thật.
- **Đừng để AI tự ý sửa docs/config.** Mình phải chỉ rõ file nào được sửa, file nào không.
- **Magic numbers là code smell.** Khi AI đặt threshold 0.6, hỏi "tại sao 0.6 mà không phải 0.8?" dẫn đến giải pháp tốt hơn.

### Điều mình sẽ làm khác nếu có thêm thời gian

- Embedding-based RAG thay vì TF-IDF (cần embedding API hoạt động)
- Session management để track conversation history thay vì stateless correction
- Real-time availability check (quán đang đông hay vắng)
- A/B test prompts để cải thiện chất lượng LLM parsing

---

## 5. Câu hỏi có thể được hỏi khi demo

**Q: Augment hay automate?**
A: Augment. AI gợi ý Top 3 + giải thích, nhưng người dùng quyết định chọn quán nào. Có thể reject và yêu cầu re-rank.

**Q: Failure mode chính là gì?**
A: LLM rate limit hoặc API key hết hạn. Xử lý bằng graceful degradation — tự động chuyển sang regex parser, system vẫn hoạt động nhưng không có AI explanations.

**Q: Phần mình làm gì?**
A: Thiết kế kiến trúc 3-Stage Chain, implement toàn bộ LLM integration (parser, explainer, client), semantic menu search (TF-IDF RAG), geo-distance ranking, off-topic guard, và sửa các bug phát hiện qua demo testing.

**Q: AI hỗ trợ phần nào?**
A: AI (Claude Code) giúp implement nhanh hơn — viết code, chạy test, debug. Nhưng mọi quyết định kiến trúc (Chain vs ReAct, TF-IDF vs embeddings, threshold logic) đều do mình đưa ra sau khi thảo luận và phản biện.
