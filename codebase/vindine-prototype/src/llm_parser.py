"""LLM-powered Vietnamese text parser for VinDine Concierge."""

import json
import logging

from src.constraint_classifier import classify_constraints
from src.llm_client import LLMError, call_llm, is_llm_available
from src.schemas import ParsedConstraints, RecommendationRequest

logger = logging.getLogger("vindine.parser")

SYSTEM_PROMPT = """You are a Vietnamese text parser for a Vinpearl resort dining concierge.
Extract structured constraints from the user's natural language description.

Return ONLY valid JSON matching this EXACT schema (use these field names exactly):
{
  "party_size": int or null,
  "current_zone": string or null,
  "has_kids": bool,
  "has_elderly": bool,
  "needs_stroller": bool,
  "needs_wheelchair": bool,
  "budget_per_person": int or null (VND, e.g. 200000),
  "voucher_required": bool,
  "voucher_type": "buffet" | "meal_credit" | "combo" | "discount" | null,
  "preferred_cuisines": list of strings (e.g. ["vietnamese", "pizza", "seafood"]),
  "dietary_needs": list of strings (e.g. ["vegetarian", "no_seafood"]),
  "quiet_preferred": bool,
  "max_distance_minutes": int or null,
  "confidence": float 0.0-1.0
}

Vietnamese keyword guide:
- "ông bà", "người lớn tuổi" → has_elderly=true, quiet_preferred=true
- "trẻ em", "con", "bé", "nhỏ" → has_kids=true
- "xe đẩy" → needs_stroller=true
- "xe lăn" → needs_wheelchair=true
- "cơm", "phở", "bún", "món Việt" → "vietnamese" in preferred_cuisines
- "pizza", "pasta", "burger", "gà rán" → "western" or "pizza" in preferred_cuisines
- "hải sản", "tôm", "cá" → "seafood" in preferred_cuisines
- "buffet" → "buffet" in preferred_cuisines; if mentioned with "voucher" → voucher_type="buffet"
- "chay", "ăn chay" → "vegetarian" in dietary_needs
- "không hải sản", "dị ứng hải sản" → "no_seafood" in dietary_needs
- "gần", "gần nhất" → max_distance_minutes=8
- "dưới X phút" → max_distance_minutes=X
- "voucher" without type → voucher_required=true, voucher_type=null
- Budget: "dưới 150k" → 150000, "200 ngàn" → 200000

Infer what the user implies. "Đi cả nhà" with elderly and children = has_elderly + has_kids.
If something is not mentioned, set it to null/false/[].
Set confidence based on how much information the user provided (0.3 for sparse, 0.9 for detailed).

IMPORTANT: Do NOT include "hard_constraints" or "soft_preferences" fields. Only return the fields listed above."""


def parse_with_llm(request: RecommendationRequest) -> ParsedConstraints | None:
    """Parse user text using LLM. Returns None if unavailable or on failure."""
    if not is_llm_available():
        return None

    user_msg = request.user_text
    if request.correction:
        user_msg += f"\n\nĐiều chỉnh: {request.correction}"

    try:
        result = call_llm(system=SYSTEM_PROMPT, user=user_msg, json_mode=True)
        data = json.loads(result)

        data.pop("hard_constraints", None)
        data.pop("soft_preferences", None)

        parsed = ParsedConstraints(
            **data,
            hard_constraints=[],
            soft_preferences=[],
        )

        if request.party_size:
            parsed.party_size = request.party_size
        if request.voucher_type:
            parsed.voucher_type = request.voucher_type
            parsed.voucher_required = True
        if request.current_zone:
            parsed.current_zone = request.current_zone

        parsed = classify_constraints(parsed)

        logger.info(
            "LLM parse success | confidence=%.2f | cuisines=%s | party=%s",
            parsed.confidence,
            parsed.preferred_cuisines,
            parsed.party_size,
        )
        return parsed

    except (LLMError, json.JSONDecodeError, Exception) as e:
        logger.warning("LLM parse failed, will fall back to regex: %s", e)
        return None
