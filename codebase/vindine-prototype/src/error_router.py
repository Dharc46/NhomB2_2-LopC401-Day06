"""Error routing and feedback learning for VinDine."""

from datetime import datetime, timezone
import json
from pathlib import Path

from src.schemas import FeedbackRequest, ParsedConstraints


REASON_TO_RECOVERY = {
    "too_noisy": "Ưu tiên quán yên tĩnh hơn và giảm điểm quán đông/ồn.",
    "too_far": "Ưu tiên khoảng cách gần hơn hoặc nới các ràng buộc khác.",
    "too_expensive": "Ưu tiên budget/kiosk/combo và giảm quán premium.",
    "no_kids_menu": "Ưu tiên quán phù hợp trẻ em và có kids menu.",
    "no_voucher": "Ưu tiên quán khớp voucher hoặc gói meal credit/combo.",
    "dietary_risk": "Ưu tiên dietary tags an toàn hơn và tránh quán có risk.",
    "other": "Ghi nhận phản hồi và re-rank bỏ gợi ý đã reject.",
}


REASON_TO_SCORE_ADJUSTMENT = {
    "too_noisy": {"quiet": 3.0},
    "too_far": {"distance": 3.0},
    "too_expensive": {"budget": 3.0},
    "no_kids_menu": {"group": 2.0},
    "no_voucher": {"voucher": 3.0},
    "dietary_risk": {"best_for": 2.0},
    "other": {},
}


def route_error(
    uncertainty: dict,
    fallback_suggestions: list[str] | None = None,
    correction_reason: str | None = None,
) -> dict:
    """Map detected uncertainty or feedback into Detect -> Route -> Recover -> Learn."""
    issues = uncertainty.get("issues", [])
    if correction_reason:
        route = "rerank_after_feedback"
        recover = [REASON_TO_RECOVERY.get(correction_reason, REASON_TO_RECOVERY["other"])]
    elif uncertainty.get("should_ask_clarification"):
        route = "ask_clarification"
        recover = [q["question"] for q in uncertainty.get("clarifying_questions", [])]
    elif fallback_suggestions:
        route = "suggest_relax_constraints"
        recover = fallback_suggestions
    elif "no_perfect_match_or_fallback_needed" in issues:
        route = "show_best_compromise"
        recover = ["Hiển thị Top 3 compromise kèm trade-off và uncertainty."]
    else:
        route = "human_review"
        recover = ["Người dùng kiểm tra voucher, khoảng cách, dietary trước khi quyết."]

    return {
        "detect": issues,
        "route": route,
        "recover": recover,
        "learn": "correction_log.jsonl" if correction_reason else None,
    }


def score_adjustments_for_reason(reason: str) -> dict[str, float]:
    """Return ranking weight multipliers for a feedback reason."""
    return dict(REASON_TO_SCORE_ADJUSTMENT.get(reason, {}))


def save_correction_signal(
    feedback: FeedbackRequest,
    parsed: ParsedConstraints,
    path: str = "data/correction_log.jsonl",
) -> bool:
    """Append a correction signal to the local JSONL learning log."""
    log_path = Path(path)
    if not log_path.is_absolute():
        log_path = Path.cwd() / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_input": feedback.original_text,
        "rejected_restaurant_id": feedback.rejected_restaurant_id,
        "reason": feedback.reason,
        "updated_constraints": parsed.model_dump(),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return True
