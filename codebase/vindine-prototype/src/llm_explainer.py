"""LLM-powered explanation generator for VinDine recommendations."""

import json
import logging

from src.llm_client import LLMError, call_llm, is_llm_available
from src.schemas import ParsedConstraints, RecommendationCard

logger = logging.getLogger("vindine.explainer")

SYSTEM_PROMPT = """You are VinDine Concierge, a friendly AI dining advisor at a Vinpearl resort.
You helped find the top restaurant recommendations for a group.
Write a brief, warm Vietnamese explanation for each recommendation.

For each restaurant, explain:
1. Vì sao quán này phù hợp (match the group's specific constraints)
2. Trade-off — điểm nào chưa hoàn hảo
3. Ai trong nhóm có thể ít hài lòng nhất và vì sao

Keep it conversational, like a real concierge talking to a guest.
2-3 sentences per restaurant. Do not invent facts not in the data provided.

Return JSON:
{
  "explanations": [
    {
      "restaurant_id": "...",
      "why_good": "...",
      "trade_off": "...",
      "least_happy": "..."
    }
  ],
  "group_summary": "One sentence summarizing the overall recommendation in Vietnamese."
}"""


def generate_explanations(
    constraints: ParsedConstraints,
    recommendations: list[RecommendationCard],
) -> dict | None:
    """Generate Vietnamese explanations for top recommendations.

    Returns dict with 'explanations' and 'group_summary', or None on failure.
    """
    if not is_llm_available() or not recommendations:
        return None

    cards_data = []
    for card in recommendations:
        cards_data.append({
            "restaurant_id": card.restaurant_id,
            "name": card.name,
            "fit_score": card.fit_score,
            "zone": card.zone,
            "distance": card.distance_text,
            "price": card.avg_price_vnd,
            "accept_voucher": card.accept_voucher,
            "voucher_match": card.voucher_match,
            "reasons": card.reasons,
            "trade_offs": card.trade_offs,
        })

    user_msg = json.dumps(
        {
            "constraints": {
                "party_size": constraints.party_size,
                "has_kids": constraints.has_kids,
                "has_elderly": constraints.has_elderly,
                "budget_per_person": constraints.budget_per_person,
                "preferred_cuisines": constraints.preferred_cuisines,
                "dietary_needs": constraints.dietary_needs,
                "quiet_preferred": constraints.quiet_preferred,
                "voucher_type": constraints.voucher_type,
            },
            "restaurants": cards_data,
        },
        ensure_ascii=False,
    )

    try:
        result = call_llm(system=SYSTEM_PROMPT, user=user_msg, json_mode=True)
        parsed = json.loads(result)
        logger.info(
            "Explanations generated for %d restaurants", len(recommendations)
        )
        return parsed
    except (LLMError, json.JSONDecodeError, Exception) as e:
        logger.warning("Explanation generation failed: %s", e)
        return None
