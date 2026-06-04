# Day 05 Lab — Khởi Động Dự Án AI Product

> Tìm vấn đề thật → gom bằng chứng → chốt một lát cắt nhỏ → viết thin SPEC → sẵn sàng build prototype trong Day 06.

Day 05 không phải một buổi học đầy đủ về AI Product Management. Đây là ngày **khởi động mini-hackathon Day 06**. Cuối ngày, nhóm chưa cần có prototype hoàn chỉnh, nhưng phải đủ rõ để sáng mai build ngay.

## Tài liệu trong folder này

Folder này được chia theo đúng việc cần làm:

| Folder / File | Dùng để làm gì |
|---|---|
| `01-invidual-workshop/app-teardown.md` | Bài mổ app AI thật: dùng thử, vẽ flow, tìm path yếu, viết finding thành quyết định product. |
| `02-group-spec/` | Bộ template cho phần nhóm: gom bằng chứng, chuyển evidence thành insight/opportunity/build slice, và viết thin SPEC cuối Day 05. |

## Cấu trúc repo nộp bài Day 06

Mỗi học viên nộp **một repo cá nhân**:

```text
Day06-MãHọcViên-HọVàTên
├── 01-invidual-workshop/
└── 02-group-spec/
```

Trong đó:

- `01-invidual-workshop/`: phần reflection cá nhân, nêu rõ vai trò, việc đã làm, phần AI hỗ trợ, và bài học sau demo.
- `02-group-spec/`: bản làm chung của nhóm. Mỗi học viên copy bản cuối vào repo cá nhân của mình.

## Đọc file nào để làm gì?

1. Làm `01-invidual-workshop/app-teardown.md` khi lớp mổ Moni / NEO / V-AI hoặc app theo track.
2. Dùng các template trong `02-group-spec/` để gom evidence, chốt insight/opportunity/build slice, và viết thin SPEC trước khi rời lớp.

## Cuối Day 05 cần có gì?

| Artifact | Cần thể hiện rõ |
|---|---|
| Evidence pack | User/pain có bằng chứng, không tự bịa. Có self-use và ít nhất một nguồn ngoài nhóm hoặc kế hoạch lấy nguồn rõ. |
| Opportunity statement | Bằng chứng nói gì sâu hơn về user; vì sao đây là việc đáng sửa. |
| Build slice | Một user, một task, một AI decision, một output. Không build cả app. |
| Auto/Aug decision | AI gợi ý hay tự làm? Human giữ quyền ở đâu? |
| Four paths | Happy, low-confidence, failure, correction. |
| Failure mode | Một lỗi nguy hiểm nhất và cách prototype xử lý. |
| Owner plan | Ai phụ trách research, SPEC, prototype, test, demo, repo. |

## Flow cuối Day 05

```text
16:00  Chọn track/app
16:15  Self-use + tìm evidence nhanh
16:45  Gom evidence -> insight
17:00  Chốt build slice + owner plan
Tối    Hoàn thiện evidence pack + thin SPEC draft
```

## Điều quan trọng nhất

- Track chỉ là **miền app thật**, không phải scope.
- Nhóm không được nộp ý tưởng kiểu "AI assistant cho healthcare" hoặc "chatbot cho travel".
- Một build slice tốt có dạng:

```text
Cho [user cụ thể] đang [task/workflow],
prototype dùng AI để [augment/automate hành động hẹp],
tạo ra [output],
và xử lý [failure mode] bằng [mitigation].
```

Ví dụ:

```text
Cho bệnh nhân lần đầu không biết chọn chuyên khoa,
prototype dùng AI để hỏi 3 câu và gợi ý 2-3 chuyên khoa phù hợp,
đồng thời chuyển sang hướng dẫn khẩn cấp/người thật nếu có red flag.
```

---

*Day 05 Lab — Batch 02 · AI Product Kickoff Sprint*
## VinDine Concierge — AI Dining Recommendation Demo

### Quick Start

```bash
cd codebase/vindine-prototype
source .venv/bin/activate
pip install -r requirements.txt
```

**Terminal 1 — API server:**
```bash
uvicorn src.api:app --reload
```

**Terminal 2 — Chatbot UI:**
```bash
streamlit run src/app.py
```

**API docs:** http://127.0.0.1:8000/docs

### LLM Setup

Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
# Edit .env with your key — Groq is free at https://console.groq.com/keys
```

Without a key, the system falls back to regex parsing (all features work, no AI explanations).

### What Was Built (Day 06 Changes)

**3-Stage LLM Chain** — replaces the original ReAct agent plan:
1. **LLM Parser** (`src/llm_parser.py`) — Vietnamese text → structured constraints via Gemini/Groq
2. **Deterministic Rank** — existing filter + weighted scoring (unchanged, 8 factors)
3. **LLM Explainer** (`src/llm_explainer.py`) — generates Vietnamese concierge-style explanations

**New files added:**
- `src/llm_client.py` — LLM client supporting Groq (free) and Google Gemini
- `src/llm_parser.py` — LLM parser with off-topic query detection
- `src/llm_explainer.py` — Vietnamese explanation generator
- `src/logger.py` — structured logging for demo visibility
- `tests/test_llm.py` — 6 tests for LLM fallback and schema validation

**Modified files:**
- `src/preference_parser.py` — LLM-first routing with regex fallback
- `src/api.py` — wired in LLM explainer, off-topic guard, logging
- `src/schemas.py` — added `lat`/`lng` to Restaurant, `ai_explanations` to response
- `src/ranking_engine.py` — geo-distance via haversine (lat/lng coordinates)
- `src/app.py` — zone picker, AI explanation display, off-topic handling
- `data/vin_restaurants.json` — added lat/lng coordinates to all 41 restaurants

**Key features:**
- Off-topic guard: rejects non-dining queries ("how to reverse linked list" → polite rejection)
- Geo-distance: real walking time calculated from coordinates when user selects a zone
- Graceful degradation: LLM fails → regex fallback → system still works
- Structured logging: all LLM calls logged with timing for demo inspection

### Tests

```bash
python3 -m pytest tests/ -v    # 48 tests, all pass
```

### Demo Paths

| Path | Input | Expected |
|------|-------|----------|
| Happy | "Gia dinh 6 nguoi, voucher buffet, ong ba muon mon Viet, tre con thich pizza" | Top 3 with AI explanations |
| Low confidence | "Tim quan an ngon" | Results + optional clarification hints |
| Failure | "Tim mon duoi 40k, co voucher buffet" | No match + fallback suggestions |
| Correction | After happy path: "Quan nay on qua, can cho yen tinh hon" | Re-ranked with quiet preference |
| Off-topic | "Chỉ tôi cách đảo linked list" | Polite rejection |
