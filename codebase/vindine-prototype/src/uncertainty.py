"""Uncertainty classification for VinDine recommendation decisions."""

from src.constraint_classifier import build_clarification_questions
from src.schemas import ParsedConstraints, RecommendationCard, RecommendationRequest, Restaurant


def _input_issues(request: RecommendationRequest, parsed: ParsedConstraints) -> list[str]:
    text = request.user_text.lower()
    issues: list[str] = []

    if not parsed.current_zone:
        issues.append("missing_location")
    if parsed.voucher_required and not parsed.voucher_type:
        issues.append("missing_voucher_type")
    if any(token in text for token in ["re", "ráº»", "gan gan", "gáº§n gáº§n"]) and (
        not parsed.budget_per_person or not parsed.max_distance_minutes
    ):
        issues.append("vague_budget_or_distance")
    if "voucher" in text and parsed.budget_per_person and parsed.budget_per_person < 100_000:
        issues.append("possible_budget_voucher_conflict")
    if parsed.quiet_preferred and parsed.has_kids and not parsed.current_zone:
        issues.append("quiet_family_context_needs_location")

    return issues


def _output_issues(
    recommendations: list[RecommendationCard] | None,
    fallback_suggestions: list[str] | None,
) -> list[str]:
    cards = recommendations or []
    issues: list[str] = []

    if fallback_suggestions:
        issues.append("no_perfect_match_or_fallback_needed")
    if len(cards) < 3:
        issues.append("fewer_than_three_matches")
    if len(cards) >= 2 and abs(cards[0].fit_score - cards[1].fit_score) <= 3:
        issues.append("top_results_close_score")
    if any(card.source_status != "verified_name" for card in cards):
        issues.append("mock_or_synthetic_source")
    if any(card.missing_info or card.assumptions for card in cards):
        issues.append("recommendation_has_assumptions")

    return issues


def _process_issues(recommendations: list[RecommendationCard] | None) -> list[str]:
    cards = recommendations or []
    issues: list[str] = []
    if any(not card.reasons for card in cards):
        issues.append("missing_reasoning")
    if any(not card.trade_offs for card in cards):
        issues.append("some_cards_have_no_tradeoff")
    if any(not card.matched_constraints for card in cards):
        issues.append("matched_constraints_not_explicit")
    return issues


def assess_uncertainty(
    request: RecommendationRequest,
    parsed: ParsedConstraints,
    recommendations: list[RecommendationCard] | None = None,
    fallback_suggestions: list[str] | None = None,
    restaurants: list[Restaurant] | None = None,
) -> dict:
    """Return input/output/process uncertainty and clarification guidance."""
    input_issues = _input_issues(request, parsed)
    output_issues = _output_issues(recommendations, fallback_suggestions)
    process_issues = _process_issues(recommendations)

    uncertainty_type: list[str] = []
    if input_issues:
        uncertainty_type.append("input")
    if output_issues:
        uncertainty_type.append("output")
    if process_issues:
        uncertainty_type.append("process")

    questions = build_clarification_questions(request, parsed)
    should_ask = bool(questions) and (
        parsed.confidence < 0.65
        or "missing_location" in input_issues
        or "missing_voucher_type" in input_issues
    )

    return {
        "uncertainty_type": uncertainty_type,
        "issues": input_issues + output_issues + process_issues,
        "clarifying_questions": [question.model_dump() for question in questions],
        "should_ask_clarification": should_ask,
        "dataset_size": len(restaurants or []),
    }
