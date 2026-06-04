"""Hard constraint filter with rejection diagnostics for the ranking pipeline."""

from collections import Counter
from dataclasses import dataclass, field

from src.schemas import ParsedConstraints, Restaurant


@dataclass
class RejectedRestaurant:
    restaurant: Restaurant
    reasons: list[str]


@dataclass
class FilterReport:
    passed: list[Restaurant]
    rejected: list[RejectedRestaurant] = field(default_factory=list)
    rejection_counts: dict[str, int] = field(default_factory=dict)


def _effective_voucher_types(restaurant: Restaurant) -> list[str]:
    return [vt for vt in restaurant.voucher_types if vt != "none"]


def _check_budget(restaurant: Restaurant, constraints: ParsedConstraints) -> str | None:
    if not constraints.budget_per_person:
        return None
    if restaurant.avg_price_vnd > constraints.budget_per_person * 1.3:
        return "budget"
    return None


def _check_voucher(
    restaurant: Restaurant, constraints: ParsedConstraints
) -> str | None:
    if not constraints.voucher_required:
        return None
    if not restaurant.accept_voucher:
        return "voucher"
    effective = _effective_voucher_types(restaurant)
    if not effective:
        return "voucher"
    if constraints.voucher_type and constraints.voucher_type not in effective:
        return "voucher"
    return None


def _check_accessibility(
    restaurant: Restaurant, constraints: ParsedConstraints
) -> str | None:
    if constraints.needs_stroller and not restaurant.stroller_accessible:
        return "stroller"
    if constraints.needs_wheelchair and not restaurant.wheelchair_accessible:
        return "wheelchair"
    return None


def _check_dietary(
    restaurant: Restaurant, constraints: ParsedConstraints
) -> str | None:
    if not constraints.dietary_needs:
        return None
    needed = set(constraints.dietary_needs)
    available = set(restaurant.dietary_tags)
    if not needed.issubset(available):
        return "dietary"
    return None


def _check_distance(
    restaurant: Restaurant, constraints: ParsedConstraints
) -> str | None:
    if not constraints.max_distance_minutes:
        return None
    if restaurant.distance_minutes > constraints.max_distance_minutes * 1.3:
        return "distance"
    return None


def apply_hard_filters(
    restaurants: list[Restaurant], constraints: ParsedConstraints
) -> FilterReport:
    """Filter restaurants by hard constraints and return diagnostics."""
    passed: list[Restaurant] = []
    rejected: list[RejectedRestaurant] = []
    counts: Counter[str] = Counter()

    checks = [
        _check_budget,
        _check_voucher,
        _check_accessibility,
        _check_dietary,
        _check_distance,
    ]

    for restaurant in restaurants:
        reasons: list[str] = []
        for check in checks:
            reason = check(restaurant, constraints)
            if reason:
                reasons.append(reason)
        if reasons:
            rejected.append(RejectedRestaurant(restaurant=restaurant, reasons=reasons))
            for reason in reasons:
                counts[reason] += 1
        else:
            passed.append(restaurant)

    return FilterReport(passed=passed, rejected=rejected, rejection_counts=dict(counts))
