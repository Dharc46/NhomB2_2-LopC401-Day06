"""Person 2 coverage for Happy, Low-confidence, Failure, and Correction paths."""

from fastapi.testclient import TestClient

from src.api import app
from src.constraint_classifier import (
    build_clarification_questions,
    classify_constraints,
    should_ask_clarification,
)
from src.preference_parser import parse_preference_text
from src.schemas import ParsedConstraints, RecommendationRequest


client = TestClient(app)


def test_happy_path_parser_classifies_hard_and_soft_constraints():
    request = RecommendationRequest(
        user_text=(
            "Nhom 6 nguoi o sanh chinh, co voucher buffet, "
            "ong ba muon mon Viet, tre con thich pizza, can xe day"
        ),
        current_zone="sanh chinh",
        voucher_type="buffet",
        party_size=6,
    )

    parsed = parse_preference_text(request)

    assert parsed.party_size == 6
    assert parsed.current_zone == "sanh chinh"
    assert parsed.has_kids is True
    assert parsed.has_elderly is True
    assert parsed.needs_stroller is True
    assert parsed.voucher_required is True
    assert parsed.voucher_type == "buffet"
    assert {"vietnamese", "pizza", "buffet"}.issubset(parsed.preferred_cuisines)
    assert {"voucher", "stroller_accessible"}.issubset(parsed.hard_constraints)
    assert {"kids", "elderly", "pizza", "vietnamese"}.issubset(
        parsed.soft_preferences
    )
    assert parsed.confidence >= 0.75

    response = client.post("/recommend", json=request.model_dump())
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["recommendations"]
    assert body["debug"]["parser"] == "parse_user_text"


def test_low_confidence_path_asks_clarification_before_confident_ranking():
    request = RecommendationRequest(user_text="Tim quan an ngon co voucher")
    parsed = parse_preference_text(request)
    questions = build_clarification_questions(request, parsed)

    assert should_ask_clarification(request, parsed) is True
    assert parsed.confidence < 0.6
    assert [question.id for question in questions] == ["current_zone", "voucher_type"]

    response = client.post("/recommend", json=request.model_dump())
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "needs_clarification"
    assert body["error_route"]["type"] == "low_confidence"
    assert [question["id"] for question in body["clarification_questions"]] == [
        "current_zone",
        "voucher_type",
    ]


def test_failure_path_no_match_returns_recovery_options():
    request = RecommendationRequest(
        user_text="Tim mon duoi 40k moi nguoi trong resort, co voucher buffet",
        current_zone="resort",
        voucher_type="buffet",
    )

    parsed = parse_preference_text(request)

    assert parsed.budget_per_person == 40_000
    assert {"budget", "voucher"}.issubset(parsed.hard_constraints)

    response = client.post("/recommend", json=request.model_dump())
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "no_match"
    assert body["recommendations"] == []
    assert body["fallback_suggestions"]
    assert body["error_route"]["next_action"] == "relax_constraint"


def test_correction_path_reclassifies_new_preference_and_reranks():
    base_request = RecommendationRequest(
        user_text="Nhom 4 nguoi o food court, muon an nhe gan nhat",
        current_zone="food court",
        party_size=4,
    )
    correction_request = RecommendationRequest(
        user_text=base_request.user_text,
        current_zone=base_request.current_zone,
        party_size=base_request.party_size,
        correction="Quan nay on ao, ong ba khong thich. Can cho yen tinh hon.",
    )

    parsed = parse_preference_text(correction_request)
    parsed = classify_constraints(parsed)

    assert parsed.has_elderly is True
    assert parsed.quiet_preferred is True
    assert "quiet" in parsed.soft_preferences

    base_body = client.post("/recommend", json=base_request.model_dump()).json()
    correction_body = client.post(
        "/recommend", json=correction_request.model_dump()
    ).json()

    assert correction_body["status"] in {"success", "needs_clarification"}
    assert correction_body["recommendations"]
    assert correction_body["parsed_constraints"]["quiet_preferred"] is True
    assert correction_body["debug"]["parser"] == "parse_user_text"
    assert (
        correction_body["recommendations"][0]["restaurant_id"]
        != base_body["recommendations"][0]["restaurant_id"]
        or correction_body["recommendations"][0]["fit_score"]
        != base_body["recommendations"][0]["fit_score"]
    )
