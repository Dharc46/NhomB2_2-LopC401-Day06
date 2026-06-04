"""LLM-powered explanation generator for VinDine recommendations."""

import json
import logging

from src.llm_client import LLMError, call_llm, is_llm_available
from src.schemas import ParsedConstraints, RecommendationCard

logger = logging.getLogger("vindine.explainer")

SYSTEM_PROMPT = """Bạn là VinDine Concierge, một trợ lý tư vấn ăn uống AI thân thiện tại resort Vinpearl.
Nhiệm vụ của bạn là giúp khách hàng tìm kiếm và hiểu rõ các gợi ý nhà hàng tốt nhất cho nhóm của họ.
Hãy viết một đoạn giải thích ngắn gọn, ấm áp bằng tiếng Việt cho mỗi đề xuất.

Với mỗi nhà hàng, hãy giải thích rõ:
1. Vì sao quán này phù hợp (khớp với các ràng buộc cụ thể của nhóm khách hàng)
2. Điểm đánh đổi (Trade-off) — điểm nào chưa thực sự hoàn hảo
3. Ai trong nhóm có thể ít hài lòng nhất và lý do tại sao

Hãy trò chuyện tự nhiên như một hướng dẫn viên resort thực thụ.
Viết từ 2-3 câu cho mỗi nhà hàng. Không tự bịa đặt các thông tin không có trong dữ liệu được cung cấp.

Trả về định dạng JSON:
{
  "explanations": [
    {
      "restaurant_id": "...",
      "why_good": "...",
      "trade_off": "...",
      "least_happy": "..."
    }
  ],
  "group_summary": "Một câu tóm tắt tổng thể đề xuất bằng tiếng Việt."
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
