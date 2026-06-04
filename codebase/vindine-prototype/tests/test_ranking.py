"""Tests for constraint_filter, ranking_engine, and fallback_handler."""

from src.constraint_filter import apply_hard_filters
from src.data_loader import load_restaurants
from src.fallback_handler import (
    generate_correction_adjustments,
    generate_fallback_suggestions,
)
from src.ranking_engine import rank_restaurants
from src.schemas import ParsedConstraints


def _base_constraints(**overrides) -> ParsedConstraints:
    defaults = {
        "confidence": 0.75,
        "preferred_cuisines": [],
        "dietary_needs": [],
        "hard_constraints": [],
        "soft_preferences": [],
    }
    defaults.update(overrides)
    return ParsedConstraints(**defaults)


def _all_restaurants():
    return load_restaurants()


class TestConstraintFilter:
    def test_no_constraints_passes_all(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints()
        report = apply_hard_filters(restaurants, constraints)

        assert len(report.passed) == len(restaurants)
        assert len(report.rejected) == 0

    def test_budget_filter_rejects_expensive(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(budget_per_person=100_000)
        report = apply_hard_filters(restaurants, constraints)

        for r in report.passed:
            assert r.avg_price_vnd <= 100_000 * 1.3
        assert "budget" in report.rejection_counts

    def test_voucher_required_filters_non_voucher(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(voucher_required=True, voucher_type="buffet")
        report = apply_hard_filters(restaurants, constraints)

        for r in report.passed:
            assert r.accept_voucher
            effective = [vt for vt in r.voucher_types if vt != "none"]
            assert "buffet" in effective
        assert "voucher" in report.rejection_counts

    def test_voucher_types_none_treated_as_no_voucher(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(voucher_required=True)
        report = apply_hard_filters(restaurants, constraints)

        for r in report.passed:
            effective = [vt for vt in r.voucher_types if vt != "none"]
            assert len(effective) > 0

    def test_dietary_filter_rejects_missing_tags(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(dietary_needs=["vegetarian"])
        report = apply_hard_filters(restaurants, constraints)

        for r in report.passed:
            assert "vegetarian" in r.dietary_tags

    def test_stroller_filter(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(needs_stroller=True)
        report = apply_hard_filters(restaurants, constraints)

        for r in report.passed:
            assert r.stroller_accessible

    def test_distance_filter(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(max_distance_minutes=10)
        report = apply_hard_filters(restaurants, constraints)

        for r in report.passed:
            assert r.distance_minutes <= 10 * 1.3

    def test_rejection_counts_are_populated(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(
            budget_per_person=50_000,
            voucher_required=True,
            voucher_type="buffet",
        )
        report = apply_hard_filters(restaurants, constraints)

        assert report.rejection_counts
        assert all(count > 0 for count in report.rejection_counts.values())


class TestRankingEngine:
    def test_returns_top_3_or_fewer(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints()
        cards, fallbacks = rank_restaurants(restaurants, constraints)

        assert len(cards) <= 3
        assert len(cards) > 0
        assert fallbacks == []

    def test_cards_sorted_by_score_descending(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(preferred_cuisines=["vietnamese", "seafood"])
        cards, _ = rank_restaurants(restaurants, constraints)

        scores = [card.fit_score for card in cards]
        assert scores == sorted(scores, reverse=True)

    def test_ranks_are_sequential(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints()
        cards, _ = rank_restaurants(restaurants, constraints)

        for i, card in enumerate(cards, start=1):
            assert card.rank == i

    def test_voucher_match_boosts_score(self):
        restaurants = _all_restaurants()
        with_voucher = _base_constraints(voucher_required=True, voucher_type="buffet")
        cards_v, _ = rank_restaurants(restaurants, with_voucher)

        if cards_v:
            assert cards_v[0].voucher_match

    def test_no_match_returns_fallback_suggestions(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(
            budget_per_person=10_000, voucher_required=True, voucher_type="buffet"
        )
        cards, fallbacks = rank_restaurants(restaurants, constraints)

        assert len(cards) == 0
        assert len(fallbacks) > 0

    def test_rejected_ids_excludes_restaurants(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints()
        cards_all, _ = rank_restaurants(restaurants, constraints)
        top_id = cards_all[0].restaurant_id

        cards_without, _ = rank_restaurants(
            restaurants, constraints, rejected_ids=[top_id]
        )
        remaining_ids = [c.restaurant_id for c in cards_without]
        assert top_id not in remaining_ids

    def test_score_adjustments_affect_scores(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(quiet_preferred=True)
        cards_normal, _ = rank_restaurants(restaurants, constraints)
        cards_boosted, _ = rank_restaurants(
            restaurants, constraints, score_adjustments={"quiet": 5.0}
        )

        assert cards_boosted[0].fit_score > cards_normal[0].fit_score

    def test_confidence_below_1(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(confidence=0.8)
        cards, _ = rank_restaurants(restaurants, constraints)

        for card in cards:
            assert 0 <= card.confidence <= 1

    def test_missing_info_includes_current_zone_when_absent(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(current_zone=None)
        cards, _ = rank_restaurants(restaurants, constraints)

        assert cards
        assert "current_zone" in cards[0].missing_info


class TestFallbackHandler:
    def test_dynamic_budget_suggestion(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(budget_per_person=50_000)
        report = apply_hard_filters(restaurants, constraints)

        suggestions = generate_fallback_suggestions(report, constraints, restaurants)
        assert any("budget" in s.lower() or "nới" in s.lower() for s in suggestions)

    def test_voucher_relaxation_suggestion(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(
            voucher_required=True, voucher_type="buffet", budget_per_person=500_000
        )
        report = apply_hard_filters(restaurants, constraints)

        suggestions = generate_fallback_suggestions(report, constraints, restaurants)
        assert any("voucher" in s.lower() for s in suggestions)

    def test_always_returns_at_least_one_suggestion(self):
        restaurants = _all_restaurants()
        constraints = _base_constraints(budget_per_person=1_000)
        report = apply_hard_filters(restaurants, constraints)

        suggestions = generate_fallback_suggestions(report, constraints, restaurants)
        assert len(suggestions) >= 1

    def test_correction_quiet_keyword(self):
        constraints = _base_constraints()
        rejected_ids, adjustments = generate_correction_adjustments(
            "Quá ồn, muốn chỗ yên tĩnh", constraints
        )

        assert "quiet" in adjustments
        assert adjustments["quiet"] == 3.0

    def test_correction_distance_keyword(self):
        constraints = _base_constraints()
        rejected_ids, adjustments = generate_correction_adjustments(
            "Quá xa", constraints
        )

        assert "distance" in adjustments
        assert adjustments["distance"] == 3.0

    def test_correction_budget_keyword(self):
        constraints = _base_constraints()
        rejected_ids, adjustments = generate_correction_adjustments(
            "Quá đắt", constraints
        )

        assert "budget" in adjustments

    def test_correction_returns_empty_rejected_ids(self):
        constraints = _base_constraints()
        rejected_ids, _ = generate_correction_adjustments("Quá ồn", constraints)

        assert rejected_ids == []


class TestAPICorrection:
    def test_correction_endpoint_works(self):
        from fastapi.testclient import TestClient

        from src.api import app

        client = TestClient(app)
        response = client.post(
            "/recommend",
            json={
                "user_text": "Nhóm 4 người gần food court, muốn ăn nhẹ",
                "current_zone": "food court",
                "voucher_type": None,
                "party_size": 4,
                "correction": "Có người ăn chay và muốn chỗ yên tĩnh",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] in {"success", "needs_clarification", "no_match"}
