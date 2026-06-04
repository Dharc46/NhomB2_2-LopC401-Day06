"""Weighted scoring engine and orchestrator for restaurant ranking."""

import math
from urllib.parse import quote_plus

from src.constraint_filter import FilterReport, apply_hard_filters
from src.fallback_handler import generate_fallback_suggestions
from src.schemas import (
    ConfidenceLabel,
    ParsedConstraints,
    RecommendationCard,
    Restaurant,
)

ZONE_COORDINATES: dict[str, tuple[float, float]] = {
    "sanh chinh": (12.2257, 109.1976),
    "cong chinh": (12.2257, 109.1976),
    "main gate": (12.2257, 109.1976),
    "lobby": (12.2150, 109.2100),
    "sanh resort": (12.2150, 109.2100),
    "resort": (12.2150, 109.2100),
    "harbour": (12.2350, 109.1940),
    "ben cang": (12.2350, 109.1940),
    "food court": (12.2218, 109.1932),
    "water park": (10.3350, 103.8550),
    "cong vien nuoc": (10.3350, 103.8550),
    "grand world": (10.3280, 103.8600),
    "folk island": (15.8500, 108.3650),
}

WALK_SPEED_KMH = 4.5


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km between two lat/lng points."""
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _walk_minutes(km: float) -> int:
    return max(1, round(km / WALK_SPEED_KMH * 60))

BASE_WEIGHTS = {
    "voucher": 25,
    "cuisine": 20,
    "group": 15,
    "budget": 15,
    "distance": 10,
    "accessibility": 5,
    "quiet": 5,
    "best_for": 5,
}

VOUCHER_REDISTRIBUTION = {
    "cuisine": 7,
    "budget": 7,
    "group": 6,
    "distance": 5,
}


def _get_weights(
    constraints: ParsedConstraints,
    score_adjustments: dict[str, float] | None = None,
) -> dict[str, float]:
    weights = dict(BASE_WEIGHTS)
    if not constraints.voucher_required:
        weights["voucher"] = 0
        for key, bonus in VOUCHER_REDISTRIBUTION.items():
            weights[key] = weights[key] + bonus
    if score_adjustments:
        for key, multiplier in score_adjustments.items():
            if key in weights:
                weights[key] = weights[key] * multiplier
    return weights


def _voucher_match(restaurant: Restaurant, constraints: ParsedConstraints) -> bool:
    if not constraints.voucher_required:
        return True
    if not restaurant.accept_voucher:
        return False
    effective = [vt for vt in restaurant.voucher_types if vt != "none"]
    if not effective:
        return False
    if constraints.voucher_type:
        return constraints.voucher_type in effective
    return True


def _score_voucher(
    restaurant: Restaurant, constraints: ParsedConstraints, weight: float
) -> tuple[float, str | None, str | None]:
    if not constraints.voucher_required:
        if restaurant.accept_voucher:
            return weight * 0.5, None, None
        return 0, None, None
    if _voucher_match(restaurant, constraints):
        return weight, "Khớp voucher yêu cầu", None
    return 0, None, "Có thể không dùng được voucher tại điểm này"


def _score_cuisine(
    restaurant: Restaurant, constraints: ParsedConstraints, weight: float
) -> tuple[float, str | None, str | None]:
    if not constraints.preferred_cuisines:
        return weight * 0.3, None, None
    matches = set(constraints.preferred_cuisines) & set(restaurant.cuisine_types)
    if matches:
        ratio = len(matches) / len(constraints.preferred_cuisines)
        return weight * ratio, "Có món phù hợp: " + ", ".join(sorted(matches)), None
    return 0, None, None


def _score_group(
    restaurant: Restaurant, constraints: ParsedConstraints, weight: float
) -> tuple[float, str | None, str | None]:
    score = 0.0
    reasons: list[str] = []
    sub_weight = weight / 3

    if constraints.has_kids:
        kid_score = restaurant.group_suitability.kids / 5
        score += sub_weight * kid_score
        if restaurant.group_suitability.kids >= 4:
            reasons.append("Phù hợp gia đình có trẻ em")

    if constraints.has_elderly:
        elderly_score = restaurant.group_suitability.elderly / 5
        score += sub_weight * elderly_score
        if restaurant.group_suitability.elderly >= 4:
            reasons.append("Dễ chịu hơn cho người lớn tuổi")

    if constraints.party_size:
        if constraints.party_size >= 6:
            score += sub_weight * (restaurant.group_suitability.large_group / 5)
        elif constraints.party_size <= 2:
            score += sub_weight * (restaurant.group_suitability.couple / 5)
        else:
            score += sub_weight * 0.6

    if (
        not constraints.has_kids
        and not constraints.has_elderly
        and not constraints.party_size
    ):
        score = weight * 0.5

    reason = ", ".join(reasons) if reasons else None
    return score, reason, None


def _score_budget(
    restaurant: Restaurant, constraints: ParsedConstraints, weight: float
) -> tuple[float, str | None, str | None]:
    if not constraints.budget_per_person:
        return weight * 0.5, None, None
    if restaurant.avg_price_vnd <= constraints.budget_per_person:
        return weight, "Nằm trong ngân sách", None
    if restaurant.avg_price_vnd <= constraints.budget_per_person * 1.3:
        return weight * 0.5, None, "Vượt ngân sách nhẹ nhưng còn trong biên linh hoạt"
    return 0, None, "Vượt ngân sách"


def _score_distance(
    restaurant: Restaurant, constraints: ParsedConstraints, weight: float
) -> tuple[float, str | None, str | None]:
    distance = restaurant.distance_minutes
    zone_bonus = 1.0

    if constraints.current_zone:
        zone_lower = constraints.current_zone.lower()
        user_coords = ZONE_COORDINATES.get(zone_lower)

        if user_coords and restaurant.lat and restaurant.lng:
            km = _haversine_km(user_coords[0], user_coords[1], restaurant.lat, restaurant.lng)
            distance = _walk_minutes(km)

        brand_lower = restaurant.brand_area.lower()
        zone_bonus = (
            1.2 if any(word in brand_lower for word in zone_lower.split()) else 1.0
        )

    if distance <= 5:
        score = weight * 1.0 * zone_bonus
        return min(score, weight), f"Khoảng cách đi bộ rất ngắn (~{distance} phút)", None
    if distance <= 10:
        score = weight * 0.7 * zone_bonus
        return min(score, weight), f"Khoảng cách đi bộ ngắn (~{distance} phút)", None
    if distance <= 15:
        return weight * 0.3, None, None
    return 0, None, f"Đi bộ khá xa (~{distance} phút)"


def _score_accessibility(
    restaurant: Restaurant, constraints: ParsedConstraints, weight: float
) -> tuple[float, str | None, str | None]:
    if not constraints.needs_stroller and not constraints.needs_wheelchair:
        return weight * 0.5, None, None
    meets = True
    if constraints.needs_stroller and not restaurant.stroller_accessible:
        meets = False
    if constraints.needs_wheelchair and not restaurant.wheelchair_accessible:
        meets = False
    if meets:
        return weight, "Đáp ứng nhu cầu xe đẩy/xe lăn", None
    return 0, None, None


def _score_quiet(
    restaurant: Restaurant, constraints: ParsedConstraints, weight: float
) -> tuple[float, str | None, str | None]:
    if not constraints.quiet_preferred:
        return weight * 0.3, None, None
    quiet_ratio = restaurant.quiet_level / 5
    score = weight * quiet_ratio
    reason = "Không gian tương đối yên tĩnh" if restaurant.quiet_level >= 4 else None
    trade_off = (
        "Có thể đông/ồn vào giờ cao điểm" if restaurant.crowd_level >= 4 else None
    )
    return score, reason, trade_off


def _score_best_for(
    restaurant: Restaurant, constraints: ParsedConstraints, weight: float
) -> tuple[float, str | None, str | None]:
    best_for_text = " ".join(restaurant.best_for).lower()
    avoid_if_text = " ".join(restaurant.avoid_if).lower()

    positive_hits = 0
    negative_hits = 0
    match_keywords: list[str] = []

    keyword_map = {
        "kids": constraints.has_kids,
        "family": constraints.has_kids,
        "elderly": constraints.has_elderly,
        "quiet": constraints.quiet_preferred,
        "voucher": constraints.voucher_required,
        "wheelchair": constraints.needs_wheelchair,
        "budget": bool(
            constraints.budget_per_person and constraints.budget_per_person < 200_000
        ),
    }

    for cuisine in constraints.preferred_cuisines:
        keyword_map[cuisine.lower()] = True

    for keyword, active in keyword_map.items():
        if not active:
            continue
        if keyword in best_for_text:
            positive_hits += 1
            match_keywords.append(keyword)
        if keyword in avoid_if_text:
            negative_hits += 1

    if negative_hits > 0:
        return 0, None, None
    if positive_hits == 0:
        return weight * 0.3, None, None

    ratio = min(positive_hits / 3, 1.0)
    return weight * ratio, None, None


_SCORERS = [
    ("voucher", _score_voucher),
    ("cuisine", _score_cuisine),
    ("group", _score_group),
    ("budget", _score_budget),
    ("distance", _score_distance),
    ("accessibility", _score_accessibility),
    ("quiet", _score_quiet),
    ("best_for", _score_best_for),
]


def _score_restaurant(
    restaurant: Restaurant,
    constraints: ParsedConstraints,
    weights: dict[str, float],
) -> tuple[float, list[str], list[str]]:
    total = 0.0
    reasons: list[str] = []
    trade_offs: list[str] = []

    for key, scorer in _SCORERS:
        score, reason, trade_off = scorer(restaurant, constraints, weights[key])
        total += score
        if reason:
            reasons.append(reason)
        if trade_off:
            trade_offs.append(trade_off)

    if not reasons:
        reasons.append("Cân bằng tốt giữa vị trí, giá và nhu cầu nhóm")
    return total, reasons, trade_offs


def _matched_constraints(
    restaurant: Restaurant,
    constraints: ParsedConstraints,
    reasons: list[str],
) -> list[str]:
    matched: list[str] = []
    if constraints.current_zone:
        matched.append(f"location_context:{constraints.current_zone}")
    if constraints.budget_per_person and restaurant.avg_price_vnd <= constraints.budget_per_person * 1.3:
        matched.append("budget")
    if constraints.voucher_required and _voucher_match(restaurant, constraints):
        matched.append("voucher")
    for cuisine in constraints.preferred_cuisines:
        if cuisine in restaurant.cuisine_types:
            matched.append(f"cuisine:{cuisine}")
    for dietary in constraints.dietary_needs:
        if dietary in restaurant.dietary_tags:
            matched.append(f"dietary:{dietary}")
    if constraints.has_kids and restaurant.group_suitability.kids >= 4:
        matched.append("kids")
    if constraints.has_elderly and restaurant.group_suitability.elderly >= 4:
        matched.append("elderly")
    if constraints.needs_stroller and restaurant.stroller_accessible:
        matched.append("stroller_accessible")
    if constraints.needs_wheelchair and restaurant.wheelchair_accessible:
        matched.append("wheelchair_accessible")
    if constraints.quiet_preferred and restaurant.quiet_level >= 4:
        matched.append("quiet")
    if constraints.max_distance_minutes and restaurant.distance_minutes <= constraints.max_distance_minutes * 1.3:
        matched.append("distance")
    if not matched:
        matched.extend(reasons[:2])
    return sorted(set(matched))


def _missed_preferences(restaurant: Restaurant, constraints: ParsedConstraints) -> list[str]:
    missed: list[str] = []
    if constraints.preferred_cuisines and not (set(constraints.preferred_cuisines) & set(restaurant.cuisine_types)):
        missed.append("preferred_cuisine")
    if constraints.quiet_preferred and restaurant.quiet_level < 4:
        missed.append("quiet")
    if constraints.has_kids and restaurant.group_suitability.kids < 4:
        missed.append("kids")
    if constraints.has_elderly and restaurant.group_suitability.elderly < 4:
        missed.append("elderly")
    if constraints.budget_per_person and restaurant.avg_price_vnd > constraints.budget_per_person:
        missed.append("ideal_budget")
    if constraints.voucher_required and not _voucher_match(restaurant, constraints):
        missed.append("voucher")
    return missed


def _explanation(
    restaurant: Restaurant,
    matched: list[str],
    missed: list[str],
    trade_offs: list[str],
) -> str:
    why = ", ".join(matched[:4]) if matched else "cân bằng tốt giữa khoảng cách, giá và nhu cầu nhóm"
    trade = "; ".join(trade_offs[:2]) if trade_offs else "không có đánh đổi lớn nào được ghi nhận"
    miss = f" Tiêu chí chưa đáp ứng: {', '.join(missed)}." if missed else ""
    return (
        f"Đề xuất {restaurant.name} vì phù hợp với {why}. "
        f"Xếp hạng này tối ưu sau khi cân đối giữa các ràng buộc, khoảng cách, khả năng tiếp cận và mức giá. "
        f"Đánh đổi: {trade}.{miss}"
    )


def _maps_url(restaurant: Restaurant) -> str:
    query = quote_plus(f"{restaurant.name} {restaurant.zone} {restaurant.brand_area}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def _least_satisfied_person(
    restaurant: Restaurant, constraints: ParsedConstraints
) -> str | None:
    if constraints.has_elderly and restaurant.group_suitability.elderly < 4:
        return "Người lớn tuổi"
    if constraints.has_kids and restaurant.group_suitability.kids < 4:
        return "Trẻ em"
    if constraints.needs_wheelchair and not restaurant.wheelchair_accessible:
        return "Khách cần xe lăn"
    if constraints.needs_stroller and not restaurant.stroller_accessible:
        return "Gia đình có xe đẩy"
    return None


def _confidence_label(confidence: float) -> ConfidenceLabel:
    if confidence < 0.6:
        return "low"
    if confidence < 0.8:
        return "medium"
    return "high"


def _card_uncertainty(
    restaurant: Restaurant, constraints: ParsedConstraints
) -> tuple[list[str], list[str]]:
    missing_info: list[str] = []
    assumptions: list[str] = []

    if not constraints.current_zone:
        missing_info.append("current_zone")
        assumptions.append(
            "Chưa biết vị trí hiện tại nên khoảng cách chỉ dùng distance_minutes mặc định của dataset."
        )
    if constraints.voucher_required and not constraints.voucher_type:
        missing_info.append("voucher_type")
        assumptions.append(
            "Chưa biết loại voucher cụ thể nên chỉ kiểm tra accept_voucher tổng quát."
        )
    if constraints.voucher_required and not _voucher_match(restaurant, constraints):
        missing_info.append("voucher_validation")
        assumptions.append(
            "Voucher cần được người dùng kiểm tra lại trước khi di chuyển."
        )
    if constraints.dietary_needs and not set(constraints.dietary_needs).issubset(
        restaurant.dietary_tags
    ):
        missing_info.append("dietary_validation")
        assumptions.append(
            "Dietary tag chưa khớp hoàn toàn, cần kiểm tra menu thực tế."
        )
    if restaurant.distance_minutes > 15:
        missing_info.append("walking_distance_confirmation")
        assumptions.append(
            "Quán khá xa, cần người dùng xác nhận nhóm có muốn đi bộ thêm không."
        )
    if constraints.quiet_preferred and restaurant.crowd_level >= 4:
        missing_info.append("crowd_level_now")
        assumptions.append(
            "Độ đông hiện tại có thể khác dataset, nên cần kiểm tra tại thời điểm đi."
        )

    return missing_info, assumptions


def rank_restaurants(
    restaurants: list[Restaurant],
    constraints: ParsedConstraints,
    rejected_ids: list[str] | None = None,
    score_adjustments: dict[str, float] | None = None,
) -> tuple[list[RecommendationCard], list[str]]:
    """Rank restaurants with weighted scoring and return Top 3 with fallbacks."""
    if rejected_ids:
        restaurants = [r for r in restaurants if r.id not in set(rejected_ids)]

    filter_report: FilterReport = apply_hard_filters(restaurants, constraints)
    candidates = filter_report.passed

    if not candidates:
        suggestions = generate_fallback_suggestions(
            filter_report, constraints, restaurants
        )
        return [], suggestions

    weights = _get_weights(constraints, score_adjustments)
    max_possible = sum(weights.values())

    scored: list[tuple[float, Restaurant, list[str], list[str]]] = []
    for restaurant in candidates:
        score, reasons, trade_offs = _score_restaurant(restaurant, constraints, weights)
        scored.append((score, restaurant, reasons, trade_offs))

    scored.sort(key=lambda item: item[0], reverse=True)

    top_score = scored[0][0] if scored else 0
    ranking_quality = top_score / max_possible if max_possible > 0 else 0.5

    recommendations: list[RecommendationCard] = []
    for rank, (score, restaurant, reasons, trade_offs) in enumerate(
        scored[:3], start=1
    ):
        missing_info, assumptions = _card_uncertainty(restaurant, constraints)
        confidence = constraints.confidence * 0.6 + ranking_quality * 0.4
        confidence = max(0.5, min(0.95, confidence))
        if missing_info:
            confidence = min(confidence, 0.79)

        matched = _matched_constraints(restaurant, constraints, reasons)
        missed = _missed_preferences(restaurant, constraints)
        recommendations.append(
            # Cards expose product-facing explanation fields so the UI can show why
            # the AI augmented the decision instead of presenting a black box rank.
            RecommendationCard(
                restaurant_id=restaurant.id,
                name=restaurant.name,
                fit_score=round(score, 2),
                rank=rank,
                zone=restaurant.zone,
                brand_area=restaurant.brand_area,
                location_hint=restaurant.location_hint,
                lat=restaurant.lat,
                lng=restaurant.lng,
                distance_text=restaurant.distance_text,
                avg_price_vnd=restaurant.avg_price_vnd,
                accept_voucher=restaurant.accept_voucher,
                voucher_match=_voucher_match(restaurant, constraints),
                reasons=reasons,
                trade_offs=trade_offs,
                matched_constraints=matched,
                missed_preferences=missed,
                explanation=_explanation(restaurant, matched, missed, trade_offs),
                google_maps_url=_maps_url(restaurant),
                least_satisfied_person=_least_satisfied_person(restaurant, constraints),
                confidence=confidence,
                confidence_label=_confidence_label(confidence),
                missing_info=missing_info,
                assumptions=assumptions,
                source_status=restaurant.source_status,
            )
        )

    return recommendations, []
