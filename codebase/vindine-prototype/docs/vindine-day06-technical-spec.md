# VinDine Concierge — Day 06 Technical Spec

## Overview

VinDine Concierge is an AI-powered dining recommendation system for Vinpearl resort guests. A group representative describes their dining needs in Vietnamese free text, and the system returns ranked restaurant recommendations with explanations, trade-offs, and fallback suggestions.

**Track:** Travel & Hospitality
**Core action:** AUGMENTATION (AI recommends, human decides)

---

## Architecture: 3-Stage Chain

```
User Vietnamese text
        │
        ▼
┌─── Stage 1: LLM Parser ─────────┐
│  Vietnamese text → ParsedJSON    │
│  Off-topic guard (is_dining?)    │
│  Regex fallback if no API key    │
└──────────────────────────────────┘
        │
        ▼
┌─── Stage 2: Deterministic ───────┐
│  menu_search.py (TF-IDF RAG)    │
│  → semantic menu matching        │
│  constraint_filter.py            │
│  → hard filter (voucher,         │
│    budget, distance, dietary)    │
│  ranking_engine.py               │
│  → 8-factor weighted scoring     │
│  → geo-distance via lat/lng      │
│  → menu similarity boost         │
│  fallback_handler.py             │
│  → if 0 results, relax          │
└──────────────────────────────────┘
        │
        ▼
┌─── Stage 3: LLM Explainer ──────┐
│  Top 3 + constraints             │
│  → Vietnamese concierge-style    │
│    explanation per restaurant    │
│  → group summary                 │
└──────────────────────────────────┘
```

### Why 3-Stage Chain, not ReAct

ReAct shines when the agent doesn't know upfront which tools to call. VinDine's workflow is always the same: parse → filter → rank → explain. The chain gives:
- **2 LLM calls** vs 3-10 in a ReAct loop
- **Deterministic ranking** — auditable, debuggable scores
- **Predictable latency** — 2-6 seconds, not 10-20
- **LLM does what LLMs are good at** — understanding Vietnamese (Stage 1) and generating explanations (Stage 3). Math and filtering (Stage 2) is done by code.

---

## LLM Integration

### Providers

| Provider | Key format | Default model | Free tier |
|----------|-----------|---------------|-----------|
| Groq (default) | `gsk_...` | `llama-3.3-70b-versatile` | 30 req/min |
| Google Gemini | `AIzaSy...` | `gemini-2.0-flash` | 60 req/min |

Config via `.env`:
```
VINDINE_LLM_PROVIDER=groq
VINDINE_LLM_KEY=gsk_your-key
VINDINE_LLM_MODEL=llama-3.3-70b-versatile
```

### Graceful Degradation

```
LLM available?
  ├── YES → LLM parser → deterministic rank → LLM explainer
  │         (if parser fails → regex fallback)
  │         (if explainer fails → no explanations, scores still shown)
  └── NO  → regex parser → deterministic rank → no explanations
```

All 48 tests pass without an LLM key. The system never crashes — it degrades.

---

## Stage 1: LLM Parser (`src/llm_parser.py`)

### Input
Vietnamese free text from user, e.g.:
> "Gia đình 6 người, có voucher buffet, ông bà muốn món Việt, trẻ con thích pizza, cần xe đẩy"

### Output
`ParsedConstraints` JSON with exact field names:
- `party_size`, `current_zone`, `has_kids`, `has_elderly`
- `needs_stroller`, `needs_wheelchair`
- `budget_per_person`, `voucher_required`, `voucher_type`
- `preferred_cuisines`, `dietary_needs`, `quiet_preferred`
- `max_distance_minutes`, `confidence` (0.0-1.0)

### Off-topic Guard
The LLM prompt includes `is_dining_related: bool`. Non-dining queries return `status: "error"` with a polite Vietnamese rejection:
> "Xin lỗi, mình chỉ hỗ trợ tìm quán ăn trong resort thôi nhé!"

### Regex Fallback (`src/preference_parser.py`)
When LLM is unavailable, `parse_preference_text()` uses regex patterns for Vietnamese keywords (budget, party size, zone, cuisines, dietary, distance, accessibility). Confidence calculated mechanically from how many fields were extracted.

---

## Stage 2: Deterministic Pipeline

### 2a. Semantic Menu Search (`src/menu_search.py`)

**Lightweight TF-IDF RAG — zero external dependencies.**

Pipeline:
1. **Index** (once at startup): tokenize each restaurant's `menu_tags`, `cuisine_types`, `dietary_tags`, `best_for` → TF-IDF vectors with unigrams + bigrams
2. **Search** (per request): tokenize user's preferred cuisines → cosine similarity against index
3. **Boost**: top matches get +10 points in ranking score

This enables queries like "bún bò Huế" to match restaurants with that specific dish, even if the user didn't say "vietnamese".

All 41 restaurants have enriched `menu_tags` with specific Vietnamese dish names (phở bò tái, bún bò Huế, cơm tấm, bánh mì, etc.).

### 2b. Hard Constraint Filter (`src/constraint_filter.py`)

Rejects restaurants violating non-negotiable constraints:
- **Budget**: `avg_price_vnd > budget × 1.3` → reject
- **Voucher**: not accepted or type mismatch → reject
- **Accessibility**: stroller/wheelchair not supported → reject
- **Dietary**: missing dietary tags → reject
- **Distance**: `distance > max × 1.3` → reject

Returns `FilterReport` with passed, rejected (with reasons), and rejection counts per constraint.

### 2c. Ranking Engine (`src/ranking_engine.py`)

8-factor weighted scoring (100 points total):

| Factor | Weight | Notes |
|--------|--------|-------|
| Voucher match | 25 | Redistributed when not required |
| Cuisine match | 20 | Intersection with preferred |
| Group suitability | 15 | kids/elderly/couple/large_group scores |
| Budget fit | 15 | Within budget or 1.3× flex |
| Distance/zone | 10 | Geo-distance via haversine when zone known |
| Accessibility | 5 | Beyond hard filter |
| Quiet level | 5 | quiet_level vs crowd_level |
| Best-for match | 5 | Keyword matching |

**Plus:** TF-IDF menu similarity boost (up to +10 points).

**Geo-distance:** When user selects a zone, haversine distance is calculated from zone coordinates to each restaurant's `lat`/`lng`. Walking time = distance / 4.5 km/h.

Zone coordinates defined in `ZONE_COORDINATES` dict (7 zones: sanh chinh, harbour, food court, sanh resort, water park, grand world, folk island).

### 2d. Fallback Handler (`src/fallback_handler.py`)

When 0 restaurants pass filters:
- **Budget**: iterates +50k steps, suggests first threshold with ≥3 options
- **Voucher**: counts restaurants without voucher requirement
- **Distance**: tries +5, +10, +15 minute increments
- **Kiosk**: scans for snack/fast_food/kiosk alternatives

### 2e. Correction Path

User rejects a recommendation and provides feedback:
> "Quán này ồn quá, cần chỗ yên tĩnh hơn"

Two mechanisms work together:
1. **LLM re-parse**: correction text appended to original query → LLM extracts updated constraints (e.g. `quiet_preferred=true`)
2. **Keyword weight boost**: `generate_correction_adjustments()` detects Vietnamese keywords → multiplies ranking weights (e.g. "ồn" → quiet × 3)

No session state needed — correction is stateless re-request.

---

## Stage 3: LLM Explainer (`src/llm_explainer.py`)

### Input
- Parsed constraints
- Top 3 recommendation cards (with scores, reasons, trade-offs)

### Output
Vietnamese concierge-style JSON:
```json
{
  "explanations": [
    {
      "restaurant_id": "...",
      "why_good": "Gateway Restaurant nằm ngay cổng chính, rất tiện cho gia đình có xe đẩy...",
      "trade_off": "Không gian có thể đông đúc vào giờ cao điểm...",
      "least_happy": "Người thích yên tĩnh có thể thấy hơi ồn..."
    }
  ],
  "group_summary": "Tôi đã chọn lọc những nhà hàng thuận tiện nhất cho gia đình bạn."
}
```

Returns `None` on failure — UI shows scores without explanations.

---

## UI: Streamlit Chatbot (`src/app.py`)

- Chat-based interface with styled restaurant cards
- **Zone picker** in sidebar (7 zones) — drives geo-distance calculations
- Handles all paths: success, needs_clarification, no_match, error (off-topic), correction
- Clarification form for follow-up questions
- AI explanation display (group summary + per-restaurant)
- Parsed constraints debug view (expandable)
- Mock offline fallbacks when backend unreachable

---

## Data: 41 Restaurants (`data/vin_restaurants.json`)

### Coverage
- **6 brand areas**: VinWonders Nha Trang, Vinpearl Harbour, Vinpearl Resort Hon Tre, VinWonders Phu Quoc, Grand World Phu Quoc, VinWonders Nam Hoi An
- **12 cuisine types**: buffet, vietnamese, asian, seafood, western, pizza, fast_food, cafe, dessert, snack, kiosk, halal_friendly
- **Per-restaurant fields** (60 total): core info, pricing, vouchers, menu (enriched with Vietnamese dish names), dietary, group suitability (1-5 scales), accessibility, atmosphere, hours, GPS coordinates (lat/lng), provenance

### Coordinates
All 41 restaurants have `lat`/`lng` coordinates based on real Vinpearl resort locations. Restaurants within the same zone cluster together with small per-restaurant jitter.

---

## Logging (`src/logger.py`)

Structured logging visible in the terminal during demo:
```
13:04:19 | vindine.api          | INFO  | Recommend request | mode=llm | text=Gia dinh 6 nguoi...
13:04:21 | vindine.llm          | INFO  | LLM call completed in 1754ms | provider=gemini | model=...
13:04:21 | vindine.parser       | INFO  | LLM parse success | confidence=0.90 | cuisines=['vietnamese']
13:04:21 | vindine.menu_search  | INFO  | Menu search 'vietnamese': top=gateway-restaurant (1.00)
13:04:23 | vindine.explainer    | INFO  | Explanations generated for 3 restaurants
13:04:23 | vindine.api          | INFO  | Recommend result | status=success | count=3 | mode=llm
```

---

## Test Coverage

**48 tests, all passing.** Tests run WITHOUT LLM key (regex fallback mode).

| Test file | Count | Coverage |
|-----------|-------|----------|
| `test_api.py` | 8 | API endpoints, all paths |
| `test_data_loader.py` | 5 | Dataset integrity, business coverage |
| `test_4_paths.py` | 4 | Happy, low-confidence, failure, correction |
| `test_ranking.py` | 25 | Filter, ranking, fallback, correction |
| `test_llm.py` | 6 | LLM fallback, schema validation |

### E2E Test Results (with LLM)

| Scenario | Status | Details |
|----------|--------|---------|
| Happy path (family group) | PASS | 9/9 checks |
| Low confidence (sparse) | PASS | 3/3 checks |
| Failure (impossible budget) | PASS | 6/6 checks |
| Correction (reject noisy) | PASS | Re-ranks with quiet preference |
| Off-topic (linked list) | PASS | Polite rejection |
| Semantic search (bún bò Huế) | PASS | Matches correct restaurants |
| Geo-distance (harbour zone) | PASS | Walking time in reasons |
| Dietary (vegetarian) | PASS | Filters correctly |
| AI explanations | PASS | Vietnamese group summary + per-restaurant |
| Simple casual query | PASS | Natural input parsed correctly |

---

## Design Decisions

### Confidence Threshold
Status is `needs_clarification` only when confidence ≤ 0.3 AND clarification questions exist. The LLM determines confidence based on input richness. No magic numbers — 0.3 means "almost nothing was parsed."

### Off-topic Guard
Built into the LLM parser prompt as `is_dining_related: bool`. Non-dining queries get early-exit in `api.py` before any ranking runs. Cleared from session state so the clarification form doesn't re-send off-topic text.

### TF-IDF vs Embeddings
We chose TF-IDF over neural embeddings because:
- Zero external dependencies (no PyTorch, no API calls)
- Instant computation (< 1ms)
- Good enough for structured menu data with specific dish names
- Bigrams capture Vietnamese dish names ("bun_bo", "com_tam", "banh_mi")

Production would use embedding-based RAG for unstructured menu descriptions.

### Geo-distance vs Static distance_minutes
The dataset had `distance_minutes` as a static field from a fixed reference point. We added `lat`/`lng` coordinates so the system calculates real walking time from the user's current zone. Falls back to static `distance_minutes` when no zone is selected.

---

## File Inventory

### New (Day 06)
| File | Lines | Purpose |
|------|-------|---------|
| `src/llm_client.py` | ~110 | LLM client (Groq + Gemini) |
| `src/llm_parser.py` | ~105 | LLM parser with off-topic guard |
| `src/llm_explainer.py` | ~80 | Vietnamese explanation generator |
| `src/menu_search.py` | ~100 | TF-IDF semantic menu search |
| `src/logger.py` | ~35 | Structured logging |
| `tests/test_llm.py` | ~65 | LLM fallback tests |
| `.env.example` | ~10 | API key template |

### Modified (Day 06)
| File | Change |
|------|--------|
| `src/preference_parser.py` | LLM-first routing in `parse_user_text()` |
| `src/api.py` | Off-topic guard, LLM explainer wiring, logging |
| `src/schemas.py` | `lat`/`lng` on Restaurant, `ai_explanations` on Response |
| `src/ranking_engine.py` | Haversine geo-distance, TF-IDF menu boost |
| `src/app.py` | Zone picker, AI explanation display, off-topic handling |
| `data/vin_restaurants.json` | lat/lng coordinates, enriched Vietnamese menu_tags |
| `requirements.txt` | Added `google-genai`, `openai` |
| `tests/test_4_paths.py` | Updated assertions for new debug fields |
| `tests/test_api.py` | Updated assertions for new status logic |

### Unchanged
| File | Purpose |
|------|---------|
| `src/constraint_filter.py` | Hard constraint filter |
| `src/constraint_classifier.py` | Constraint classification |
| `src/fallback_handler.py` | Fallback suggestions |
| `src/data_loader.py` | Dataset loading |
| `src/mock_parser.py` | Reference stub |
| `src/mock_ranking.py` | Reference stub |
| `tests/test_ranking.py` | Ranking tests (25) |
| `tests/test_data_loader.py` | Data tests (5) |
