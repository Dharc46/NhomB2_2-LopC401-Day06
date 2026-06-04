"""Tests for LLM integration — fallback behavior and schema validation."""

import json

from fastapi.testclient import TestClient

from src.api import app
from src.llm_client import is_llm_available
from src.llm_explainer import generate_explanations
from src.llm_parser import parse_with_llm
from src.schemas import ParsedConstraints, RecommendationRequest


client = TestClient(app)


def test_llm_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("VINDINE_LLM_KEY", raising=False)
    assert is_llm_available() is False


def test_llm_parser_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("VINDINE_LLM_KEY", raising=False)
    request = RecommendationRequest(user_text="6 nguoi, voucher buffet")
    result = parse_with_llm(request)
    assert result is None


def test_llm_explainer_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("VINDINE_LLM_KEY", raising=False)
    result = generate_explanations(
        ParsedConstraints(confidence=0.8),
        [],
    )
    assert result is None


def test_llm_json_validates_against_parsed_constraints():
    """Verify that a well-formed LLM JSON response parses into ParsedConstraints."""
    llm_json = json.dumps({
        "party_size": 6,
        "current_zone": "sanh chinh",
        "has_kids": True,
        "has_elderly": True,
        "needs_stroller": True,
        "needs_wheelchair": False,
        "budget_per_person": None,
        "voucher_required": True,
        "voucher_type": "buffet",
        "preferred_cuisines": ["vietnamese", "pizza", "buffet"],
        "dietary_needs": [],
        "quiet_preferred": False,
        "max_distance_minutes": None,
        "confidence": 0.85,
    })
    parsed = ParsedConstraints.model_validate_json(llm_json)
    assert parsed.party_size == 6
    assert parsed.has_kids is True
    assert parsed.has_elderly is True
    assert parsed.voucher_type == "buffet"
    assert "vietnamese" in parsed.preferred_cuisines


def test_full_pipeline_works_without_llm(monkeypatch):
    monkeypatch.delenv("VINDINE_LLM_KEY", raising=False)
    response = client.post("/recommend", json={
        "user_text": "gia dinh 4 nguoi, tre em thich pizza",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["debug"]["mode"] == "regex"
    assert data["debug"]["parser"] == "regex_parser"
    assert data["ai_explanations"] is None


def test_response_includes_ai_explanations_field():
    response = client.post("/recommend", json={
        "user_text": "6 nguoi, voucher buffet, ong ba muon mon Viet",
        "voucher_type": "buffet",
        "party_size": 6,
    })
    assert response.status_code == 200
    data = response.json()
    assert "ai_explanations" in data
