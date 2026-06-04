"""Dynamic fallback suggestions and correction-path adjustments."""

import re

from src.constraint_filter import FilterReport
from src.schemas import ParsedConstraints, Restaurant


def generate_fallback_suggestions(
    filter_report: FilterReport,
    constraints: ParsedConstraints,
    restaurants: list[Restaurant],
) -> list[str]:
    """Build context-aware suggestions based on which constraints killed the most options."""
    suggestions: list[str] = []
    counts = filter_report.rejection_counts

    ranked_blockers = sorted(counts.items(), key=lambda item: item[1], reverse=True)

    for blocker, _ in ranked_blockers:
        if blocker == "budget" and constraints.budget_per_person:
            suggestion = _budget_suggestion(constraints, restaurants)
            if suggestion:
                suggestions.append(suggestion)

        elif blocker == "voucher":
            without_voucher = sum(
                1 for r in restaurants if _passes_non_voucher_filters(r, constraints)
            )
            if without_voucher > 0:
                suggestions.append(
                    f"Bỏ yêu cầu voucher sẽ mở ra {without_voucher} lựa chọn"
                )

        elif blocker == "distance" and constraints.max_distance_minutes:
            suggestion = _distance_suggestion(constraints, restaurants)
            if suggestion:
                suggestions.append(suggestion)

        elif blocker in ("stroller", "wheelchair"):
            suggestions.append(
                "Mở rộng lựa chọn bằng cách bỏ yêu cầu xe đẩy/xe lăn nếu có thể"
            )

        elif blocker == "dietary":
            suggestions.append("Nới lỏng yêu cầu dietary để mở thêm lựa chọn")

    kiosk_alternatives = _find_kiosk_alternatives(restaurants, constraints)
    if kiosk_alternatives:
        names = ", ".join(kiosk_alternatives[:3])
        suggestions.append(f"Thử kiosk/snack gần đây: {names}")

    if not suggestions:
        suggestions.append("Nới budget thêm 50.000-100.000 VND/người")
        suggestions.append("Chuyển sang kiosk/snack/combo gần nhất")

    return suggestions[:5]


def _budget_suggestion(
    constraints: ParsedConstraints, restaurants: list[Restaurant]
) -> str | None:
    budget = constraints.budget_per_person
    if not budget:
        return None
    for step in range(1, 7):
        threshold = budget + step * 50_000
        count = sum(1 for r in restaurants if r.avg_price_vnd <= threshold * 1.3)
        if count >= 3:
            return (
                f"Nới budget lên {threshold // 1000}k/người sẽ mở ra {count} lựa chọn"
            )
    return None


def _distance_suggestion(
    constraints: ParsedConstraints, restaurants: list[Restaurant]
) -> str | None:
    max_dist = constraints.max_distance_minutes
    if not max_dist:
        return None
    for extra in (5, 10, 15):
        new_max = max_dist + extra
        count = sum(1 for r in restaurants if r.distance_minutes <= new_max * 1.3)
        if count >= 3:
            return f"Mở rộng khoảng cách lên {new_max} phút sẽ mở ra {count} lựa chọn"
    return None


def _passes_non_voucher_filters(
    restaurant: Restaurant, constraints: ParsedConstraints
) -> bool:
    if (
        constraints.budget_per_person
        and restaurant.avg_price_vnd > constraints.budget_per_person * 1.3
    ):
        return False
    if constraints.needs_stroller and not restaurant.stroller_accessible:
        return False
    if constraints.needs_wheelchair and not restaurant.wheelchair_accessible:
        return False
    if constraints.dietary_needs:
        if not set(constraints.dietary_needs).issubset(set(restaurant.dietary_tags)):
            return False
    if (
        constraints.max_distance_minutes
        and restaurant.distance_minutes > constraints.max_distance_minutes * 1.3
    ):
        return False
    return True


def _find_kiosk_alternatives(
    restaurants: list[Restaurant], constraints: ParsedConstraints
) -> list[str]:
    kiosk_cuisines = {"snack", "fast_food", "kiosk"}
    alternatives: list[str] = []
    for r in restaurants:
        is_kiosk = (
            bool(set(r.cuisine_types) & kiosk_cuisines)
            or "food court" in r.zone.lower()
        )
        if not is_kiosk:
            continue
        if constraints.needs_stroller and not r.stroller_accessible:
            continue
        if constraints.needs_wheelchair and not r.wheelchair_accessible:
            continue
        alternatives.append(r.name)
    return alternatives


_CORRECTION_KEYWORDS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"[ồôo][nồ]|ồm", re.IGNORECASE), "quiet", 3.0),
    (re.compile(r"\bxa\b", re.IGNORECASE), "distance", 3.0),
    (re.compile(r"[đd][aắ]t|m[aắ]c", re.IGNORECASE), "budget", 3.0),
]

_CUISINE_REJECT_PATTERN = re.compile(r"không thích\s+(\w+)", re.IGNORECASE)


def generate_correction_adjustments(
    correction_text: str, constraints: ParsedConstraints
) -> tuple[list[str], dict[str, float]]:
    """Parse Vietnamese correction text into rejected IDs and score adjustments."""
    rejected_ids: list[str] = []
    score_adjustments: dict[str, float] = {}

    for pattern, key, multiplier in _CORRECTION_KEYWORDS:
        if pattern.search(correction_text):
            score_adjustments[key] = multiplier

    cuisine_match = _CUISINE_REJECT_PATTERN.search(correction_text)
    if cuisine_match:
        unwanted = cuisine_match.group(1).lower()
        if unwanted in constraints.preferred_cuisines:
            constraints.preferred_cuisines.remove(unwanted)

    return rejected_ids, score_adjustments
