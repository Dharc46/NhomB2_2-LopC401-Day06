# Person 3 — AI + Ranking Core Implementation Plan

## Context

**Project:** VinDine Concierge — AI dining recommendation system for Vinpearl resort guests. A group representative inputs their party's needs, and the AI ranks Top 3 restaurants with fit scores, trade-offs, and fallback suggestions.

**Why this change:** Person 1 has completed the foundation (FastAPI endpoints, 41-restaurant dataset, Pydantic schemas, stub parser + ranking). All 13 tests pass. Person 3 must now replace the stub ranking logic with production-quality modules: a hard constraint filter, a weighted scoring engine, and a dynamic fallback handler. The stubs work but have gaps: no distance filtering, flat static fallbacks, no correction-path support, ignores `best_for`/`avoid_if`/`party_size` fields, and no zone-aware scoring.

**Intended outcome:** Three new modules that drop in as replacements for `mock_ranking.py`, making the ranking smarter, the fallbacks dynamic, and the correction path functional — while keeping all existing tests green.

---

## Deliverables

### 1. `/src/constraint_filter.py` — Hard Constraint Filter

Extracts and improves the hard-filter logic from `mock_ranking.py`. Returns filtered candidates **plus** a diagnostic report of why restaurants were rejected (powers the fallback handler).

**Key function:**
```python
def apply_hard_filters(restaurants, constraints) -> FilterReport
```

`FilterReport` is a dataclass with `passed`, `rejected` (with reasons), and `rejection_counts` (e.g. `{"budget": 15, "voucher": 8}`).

**Improvements over stub:**
- Enforce `max_distance_minutes` (stub ignores it entirely) with 1.3x flex (matches stub's budget flex convention)
- Check ALL `dietary_needs` against `restaurant.dietary_tags` using set intersection — reject if ANY hard dietary need is missing
- Track rejection diagnostics per constraint for fallback handler
- Voucher filtering: hard-filter when `voucher_required=True` (fixes stub bug where voucher was soft_preference)
- Handle `voucher_types: ["none"]` in dataset — treat as `accept_voucher=False`

**Data quirk:** 20 restaurants in the dataset have `voucher_types: ["none"]` instead of `[]`. The filter must treat `"none"` as no voucher support.

**Reuse from stub:** `_passes_hard_filters()` and `_voucher_match()` logic from [mock_ranking.py](src/mock_ranking.py) — same rules, better structure.

---

### 2. `/src/ranking_engine.py` — Weighted Scoring Engine + Orchestrator

The main module. Contains scoring logic and the orchestrator function that `api.py` calls.

**Key function (same return signature as stub):**
```python
def rank_restaurants(restaurants, constraints, rejected_ids=None, score_adjustments=None)
    -> tuple[list[RecommendationCard], list[str]]
```

**Scoring weights (normalized 0-100):**

| Component | Weight | Notes |
|-----------|--------|-------|
| Voucher match | 25 | Redistributed when not required |
| Cuisine match | 20 | Checks `cuisine_types` intersection |
| Group suitability | 15 | kids + elderly scores from dataset |
| Budget fit | 15 | How well price fits budget |
| Distance/zone | 10 | Zone-aware when `current_zone` known |
| Accessibility | 5 | Bonus beyond hard filter |
| Quiet/ambiance | 5 | `quiet_level` vs `crowd_level` |
| Best-for match | 5 | `best_for`/`avoid_if` tag matching |

**Improvements over stub:**
- Uses `best_for` and `avoid_if` fields (stub ignores them)
- Scores `party_size` against `group_suitability.large_group` / `.couple`
- Zone-aware distance scoring: when `current_zone` is set, prefer restaurants in the same `brand_area` and use `distance_minutes` from dataset (no custom adjacency map — dataset already has per-restaurant distances)
- Correction path: `rejected_ids` excludes previously rejected restaurants, `score_adjustments` multiplies specific weight components
- Score breakdown transparency in each `ScoredRestaurant`
- Weight redistribution when voucher is not required: 25pts spread proportionally across cuisine (+7), budget (+7), group suitability (+6), distance (+5)
- Improved confidence: base on (parser confidence * 0.6 + ranking quality * 0.4) where ranking quality = top score / max possible score

**`score_adjustments` keys:** `"voucher"`, `"cuisine"`, `"group"`, `"budget"`, `"distance"`, `"accessibility"`, `"quiet"`, `"best_for"`. Each value is a float multiplier (e.g., 2.0 = double the weight).

**LLM explanation generator:** Template-based by default using Vietnamese strings built from score breakdown (e.g., "Khop voucher buffet, co mon Viet va pizza, phu hop tre em"). If `VINDINE_LLM_KEY` env var is set, optionally call OpenAI-compatible API to generate more natural Vietnamese explanations — but this is NOT required for MVP.

**Reuse:** `_score_restaurant()`, `_least_satisfied_person()`, `_card_uncertainty()`, `_confidence_label()` patterns from [mock_ranking.py](src/mock_ranking.py).

---

### 3. `/src/fallback_handler.py` — Dynamic Fallback Handler

Replaces the static `FALLBACK_SUGGESTIONS` list with context-aware suggestions.

**Key functions:**
```python
def generate_fallback_suggestions(filter_report, constraints, restaurants) -> list[str]
def generate_correction_adjustments(correction_text, constraints) -> tuple[list[str], dict[str, float]]
```

**Improvements over stub:**
- Analyzes `FilterReport.rejection_counts` to target the constraint that killed the most options
- Quantified suggestions algorithm: for budget, iterate price thresholds in 50k steps above current budget, count how many restaurants pass at each step, pick the first step that unlocks >= 3 options. E.g., "Noi budget len 250k/nguoi se mo ra 8 lua chon"
- For voucher: count how many restaurants pass without the voucher filter. E.g., "Bo yeu cau voucher se mo ra 15 lua chon"
- For distance: try 5, 10, 15 min increments above current max
- Names specific kiosk/food-court alternatives by scanning `cuisine_types` for `"snack"`, `"fast_food"`, `"kiosk"` or `zone` containing `"food court"`
- Correction parsing via Vietnamese keyword matching:
  - `"on"` / `"om"` → `{"quiet": 3.0}` (triple quiet weight)
  - `"xa"` → `{"distance": 3.0}`
  - `"dat"` / `"mac"` → `{"budget": 3.0}`
  - `"khong thich [cuisine]"` → remove that cuisine from preferred, no score_adjustment needed

---

## Integration into `api.py`

Minimal change — swap imports and calls:

```python
# Line 11-12: change import
from src.ranking_engine import rank_restaurants  # was: from src.mock_ranking import rank_restaurants_stub

# Line 170: change call (+ correction path)
if request.correction:
    from src.fallback_handler import generate_correction_adjustments
    rejected_ids, score_adjustments = generate_correction_adjustments(request.correction, parsed_constraints)
    recommendations, fallback_suggestions = rank_restaurants(restaurants, parsed_constraints, rejected_ids, score_adjustments)
else:
    recommendations, fallback_suggestions = rank_restaurants(restaurants, parsed_constraints)
```

---

## Call Flow

```
api.py: recommend()
  → ranking_engine.py: rank_restaurants()
      → constraint_filter.py: apply_hard_filters() → FilterReport
      → If empty: fallback_handler.py: generate_fallback_suggestions() → return ([], suggestions)
      → For each passed: score_restaurant() → ScoredRestaurant
      → Sort desc, take top 3, build RecommendationCards
      → return (cards, [])
```

---

## Implementation Order

1. `src/constraint_filter.py` — no deps on other new modules
2. `src/fallback_handler.py` — depends on `FilterReport` from step 1
3. `src/ranking_engine.py` — orchestrates both, builds cards
4. `src/api.py` integration — import swap + correction wiring
5. `tests/test_ranking.py` — unit tests for the new modules
6. Run all existing tests to verify backward compatibility

---

## Verification

1. **All 13 existing tests must pass** — the return signature is identical to the stub
2. **New test file `tests/test_ranking.py`** covering:
   - Hard filters: budget, accessibility, dietary, distance, voucher
   - Filter report tracks rejection counts
   - Scoring: voucher match, cuisine, group suitability, best_for/avoid_if
   - Top-3 ordering correctness
   - Fallback: dynamic budget/voucher suggestions
   - Correction path: "qua on" boosts quiet weight
3. **Manual API test:** run `uvicorn src.api:app` and POST to `/recommend` with happy/failure/correction payloads from [docs/recommend_examples.json](docs/recommend_examples.json)

---

## Notes

- `mock_ranking.py` stays intact as reference — no modifications
- No LLM API key needed: explanations use Vietnamese template strings by default
- All new code uses existing Pydantic models from [schemas.py](src/schemas.py) — no schema changes needed
