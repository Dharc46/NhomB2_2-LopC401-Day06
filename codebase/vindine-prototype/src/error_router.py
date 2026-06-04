"""Error routing and feedback learning for VinDine."""

from datetime import datetime, timezone
import json
from pathlib import Path

from src.schemas import FeedbackRequest, ParsedConstraints


REASON_TO_RECOVERY = {
    "too_noisy": "Æ¯u tiÃªn quÃ¡n yÃªn tÄ©nh hÆ¡n vÃ  giáº£m Ä‘iá»ƒm quÃ¡n Ä‘Ã´ng/á»“n.",
    "too_far": "Æ¯u tiÃªn khoáº£ng cÃ¡ch gáº§n hÆ¡n hoáº·c ná»›i cÃ¡c rÃ ng buá»™c khÃ¡c.",
    "too_expensive": "Æ¯u tiÃªn budget/kiosk/combo vÃ  giáº£m quÃ¡n premium.",
    "no_kids_menu": "Æ¯u tiÃªn quÃ¡n phÃ¹ há»£p tráº» em vÃ  cÃ³ kids menu.",
    "no_voucher": "Æ¯u tiÃªn quÃ¡n khá»›p voucher hoáº·c gÃ³i meal credit/combo.",
    "dietary_risk": "Æ¯u tiÃªn dietary tags an toÃ n hÆ¡n vÃ  trÃ¡nh quÃ¡n cÃ³ risk.",
    "other": "Ghi nháº­n pháº£n há»“i vÃ  re-rank bá» gá»£i Ã½ Ä‘Ã£ reject.",
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
        recover = ["Hiá»ƒn thá»‹ Top 3 compromise kÃ¨m trade-off vÃ  uncertainty."]
    else:
        route = "human_review"
        recover = ["NgÆ°á»i dÃ¹ng kiá»ƒm tra voucher, khoáº£ng cÃ¡ch, dietary trÆ°á»›c khi quyáº¿t."]

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
