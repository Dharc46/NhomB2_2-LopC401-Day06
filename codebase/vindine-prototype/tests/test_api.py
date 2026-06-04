from fastapi.testclient import TestClient

from src.api import app


client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["dataset_loaded"] is True
    assert body["restaurant_count"] >= 35


def test_restaurants_returns_list():
    response = client.get("/restaurants")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_restaurant_detail_returns_record_by_id():
    response = client.get("/restaurants/gateway-restaurant")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "gateway-restaurant"
    assert body["name"] == "Gateway Restaurant"


def test_restaurant_detail_returns_404_for_unknown_id():
    response = client.get("/restaurants/not-a-real-restaurant")

    assert response.status_code == 404


def test_dataset_summary_returns_total_count():
    response = client.get("/dataset/summary")

    assert response.status_code == 200
    assert response.json()["total_count"] >= 35


def test_recommend_happy_path_has_parsed_constraints():
    response = client.post(
        "/recommend",
        json={
            "user_text": "Nhóm 6 người ở sảnh chính, có ông bà và trẻ con, có voucher buffet, muốn món Việt hoặc pizza, cần xe đẩy",
            "current_zone": "sảnh chính",
            "voucher_type": "buffet",
            "party_size": 6,
            "correction": None,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"success", "needs_clarification"}
    assert body["parsed_constraints"]["has_kids"] is True
    assert body["parsed_constraints"]["has_elderly"] is True
    assert body["parsed_constraints"]["needs_stroller"] is True
    assert body["parsed_constraints"]["voucher_required"] is True
    assert body["recommendations"]
    first_card = body["recommendations"][0]
    assert first_card["confidence_label"] in {"low", "medium", "high"}
    assert "missing_info" in first_card
    assert "assumptions" in first_card
    assert body["human_role"]["decider"] == "Người đại diện nhóm chọn quán cuối cùng"


def test_recommend_low_confidence_needs_clarification():
    response = client.post(
        "/recommend",
        json={"user_text": "Tìm quán ăn ngon", "current_zone": None, "voucher_type": None, "party_size": None, "correction": None},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert body["clarification_questions"]
    assert body["error_route"]["type"] == "low_confidence"
    assert body["error_route"]["next_action"] == "ask_clarification"
    assert body["recommendations"][0]["confidence"] < 1
    assert "current_zone" in body["recommendations"][0]["missing_info"]


def test_recommend_failure_returns_no_match_or_fallbacks():
    response = client.post(
        "/recommend",
        json={
            "user_text": "Tìm món dưới 40000/người trong resort, có voucher buffet",
            "current_zone": "resort",
            "voucher_type": "buffet",
            "party_size": None,
            "correction": None,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_match" or body["fallback_suggestions"]
    if body["status"] == "no_match":
        assert body["error_route"]["type"] == "no_match"
        assert body["error_route"]["next_action"] == "relax_constraint"
