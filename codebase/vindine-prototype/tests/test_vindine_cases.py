"""Boss-prompt acceptance tests for VinDine Concierge."""

from fastapi.testclient import TestClient

from src.api import app


client = TestClient(app)


def test_happy_path_recommendation_has_explainability():
    response = client.post(
        "/recommend",
        json={
            "text": "Nha minh 6 nguoi o sanh Vinpearl, co ong ba va 2 tre em, muon mon Viet hoac pizza, co voucher buffet, di bo duoi 8 phut.",
            "current_zone": "sanh chinh",
            "voucher_type": "buffet",
            "party_size": 6,
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["type"] == "recommendation"
    assert len(body["top_results"]) == 3
    first = body["top_results"][0]
    assert first["explanation"]
    assert "matched_constraints" in first
    assert "trade_offs" in first
    assert "least_satisfied_person" in first


def test_low_confidence_asks_location_or_voucher_type():
    response = client.post(
        "/recommend",
        json={"text": "Co voucher Vin, tim quan gan gan cho gia dinh."},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["type"] == "clarification"
    question_ids = {item["id"] for item in body["questions"]}
    assert {"current_zone", "voucher_type"} & question_ids


def test_constraint_conflict_has_clear_fallback_or_clarification():
    response = client.post(
        "/recommend",
        json={
            "text": "7 nguoi, co ong ba, muon yen tinh, co tre em, dung voucher buffet, duoi 70k/nguoi.",
            "current_zone": "sanh chinh",
            "voucher_type": "buffet",
            "party_size": 7,
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["type"] in {"no_match", "recommendation", "clarification"}
    assert body["fallback_options"] or body["top_results"] or body["questions"]
    if body["top_results"]:
        assert body["top_results"][0]["trade_offs"] or body["top_results"][0]["missed_preferences"]


def test_accessibility_first_respects_stroller_and_distance_when_available():
    response = client.post(
        "/recommend",
        json={
            "text": "Gia dinh co ong ba di cham va em be dung xe day, muon an mon Viet, khong di bo qua 5 phut.",
            "current_zone": "sanh chinh",
            "party_size": 5,
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["type"] == "recommendation"
    for card in body["top_results"]:
        assert "stroller_accessible" in card["matched_constraints"]


def test_dietary_hard_constraint_avoids_seafood_only():
    response = client.post(
        "/recommend",
        json={
            "text": "5 nguoi, 1 nguoi an chay, 1 nguoi di ung hai san, muon gan cong vien nuoc.",
            "current_zone": "water park",
            "party_size": 5,
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["type"] == "recommendation"
    for card in body["top_results"]:
        assert "dietary:vegetarian" in card["matched_constraints"]
        assert "dietary:non_seafood_options" in card["matched_constraints"]


def test_no_perfect_match_returns_recoverable_path():
    response = client.post(
        "/recommend",
        json={
            "text": "Tim quan gan nhat, duoi 50k/nguoi, co mon chay, yen tinh, dung voucher.",
            "current_zone": "sanh chinh",
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["type"] in {"clarification", "no_match", "recommendation"}
    assert body["fallback_options"] or body["questions"] or body["error_flow"]["recover"]


def test_feedback_rerank_saves_correction():
    original = "6 nguoi, co tre em, muon an nhanh gan sanh."
    first = client.post("/recommend", json={"text": original, "current_zone": "sanh chinh"}).json()
    rejected_id = first["top_results"][0]["restaurant_id"]

    response = client.post(
        "/feedback",
        json={
            "original_text": original,
            "rejected_restaurant_id": rejected_id,
            "reason": "too_noisy",
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["type"] == "reranked"
    assert body["correction_saved"] is True
    assert rejected_id not in [item["restaurant_id"] for item in body["top_results"]]


def test_explainability_mentions_not_rating_only():
    response = client.post(
        "/recommend",
        json={
            "text": "Chon quan rating cao nhat gan sanh cho gia dinh co tre em va ong ba.",
            "current_zone": "sanh chinh",
            "party_size": 5,
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["top_results"]
    explanation = body["top_results"][0]["explanation"].lower()
    assert "not simply chosen by rating" in explanation
    assert body["top_results"][0]["matched_constraints"]
