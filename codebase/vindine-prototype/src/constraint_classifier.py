"""Constraint classification and clarification helpers for VinDine."""

from src.schemas import (
    ClarificationQuestion,
    ParsedConstraints,
    RecommendationRequest,
)


HARD_CONSTRAINTS = {
    "budget",
    "voucher",
    "stroller_accessible",
    "wheelchair_accessible",
    "vegetarian",
    "non_seafood_options",
    "distance",
}

SOFT_PREFERENCES = {
    "kids",
    "elderly",
    "quiet",
    "voucher",
    "vietnamese",
    "pizza",
    "buffet",
    "seafood",
    "snack",
    "nearby",
}


def classify_constraints(parsed: ParsedConstraints) -> ParsedConstraints:
    """Normalize hard and soft constraint labels on a parsed request."""
    hard = set(parsed.hard_constraints)
    soft = set(parsed.soft_preferences)

    if parsed.budget_per_person:
        hard.add("budget")
    if parsed.voucher_required:
        hard.add("voucher")
        soft.add("voucher")
    if parsed.needs_stroller:
        hard.add("stroller_accessible")
    if parsed.needs_wheelchair:
        hard.add("wheelchair_accessible")
    if parsed.max_distance_minutes:
        hard.add("distance")

    for dietary_need in parsed.dietary_needs:
        hard.add(dietary_need)

    if parsed.has_kids:
        soft.add("kids")
    if parsed.has_elderly:
        soft.add("elderly")
    if parsed.quiet_preferred:
        soft.add("quiet")
    for cuisine in parsed.preferred_cuisines:
        soft.add(cuisine)

    parsed.hard_constraints = sorted(hard)
    parsed.soft_preferences = sorted(soft)
    return parsed


def missing_required_info(
    request: RecommendationRequest, parsed: ParsedConstraints
) -> list[str]:
    """Return the minimum fields needed before recommendations are high-confidence."""
    missing: list[str] = []

    if not parsed.current_zone:
        missing.append("current_zone")
    if parsed.voucher_required and not parsed.voucher_type:
        missing.append("voucher_type")

    text = request.user_text.lower()
    if any(token in text for token in ["nhom", "nhóm", "gia dinh", "gia đình"]):
        if not parsed.party_size:
            missing.append("party_size")

    return missing


def build_clarification_questions(
    request: RecommendationRequest, parsed: ParsedConstraints
) -> list[ClarificationQuestion]:
    """Build user-facing clarification questions for low-confidence parses."""
    questions: list[ClarificationQuestion] = []
    missing = missing_required_info(request, parsed)

    if "current_zone" in missing:
        questions.append(
            ClarificationQuestion(
                id="current_zone",
                question="Bạn đang ở khu/sảnh nào trong Vinpearl?",
                options=["Cổng chính", "Sảnh resort", "Harbour", "Food Court"],
            )
        )
    if "voucher_type" in missing:
        questions.append(
            ClarificationQuestion(
                id="voucher_type",
                question="Voucher của bạn là buffet, meal credit, combo hay discount?",
                options=["buffet", "meal_credit", "combo", "discount"],
            )
        )
    if "party_size" in missing:
        questions.append(
            ClarificationQuestion(
                id="party_size",
                question="Nhóm mình có bao nhiêu người?",
                options=["2-3 người", "4-6 người", "7+ người"],
            )
        )

    return questions[:2]


def should_ask_clarification(
    request: RecommendationRequest,
    parsed: ParsedConstraints,
    threshold: float = 0.6,
) -> bool:
    """Decide whether the system should ask before showing a confident result."""
    return parsed.confidence < threshold or bool(missing_required_info(request, parsed))
