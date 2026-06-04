"""Temporary ranking logic for UI and API integration testing."""

from src.schemas import ConfidenceLabel, ParsedConstraints, RecommendationCard, Restaurant


FALLBACK_SUGGESTIONS = [
    "Noi budget them 50.000-100.000 VND/nguoi",
    "Chuyen sang kiosk/snack/combo gan nhat",
    "Mo rong khoang cach di bo them 5-10 phut",
    "Bo dieu kien voucher neu khong bat buoc",
    "Chon food court de can bang khau vi nhom",
]


def _voucher_match(restaurant: Restaurant, constraints: ParsedConstraints) -> bool:
    if not constraints.voucher_required:
        return True
    if not restaurant.accept_voucher:
        return False
    if constraints.voucher_type:
        return constraints.voucher_type in restaurant.voucher_types
    return True


def _passes_hard_filters(restaurant: Restaurant, constraints: ParsedConstraints) -> bool:
    if constraints.budget_per_person and restaurant.avg_price_vnd > constraints.budget_per_person * 1.3:
        return False
    if constraints.needs_stroller and not restaurant.stroller_accessible:
        return False
    if constraints.needs_wheelchair and not restaurant.wheelchair_accessible:
        return False
    if "vegetarian" in constraints.dietary_needs and "vegetarian" not in restaurant.dietary_tags:
        return False
    if "non_seafood_options" in constraints.dietary_needs and "non_seafood_options" not in restaurant.dietary_tags:
        return False
    return True


def _least_satisfied_person(restaurant: Restaurant, constraints: ParsedConstraints) -> str | None:
    if constraints.has_elderly and restaurant.group_suitability.elderly < 4:
        return "Nguoi lon tuoi"
    if constraints.has_kids and restaurant.group_suitability.kids < 4:
        return "Tre em"
    if constraints.needs_wheelchair and not restaurant.wheelchair_accessible:
        return "Khach can xe lan"
    if constraints.needs_stroller and not restaurant.stroller_accessible:
        return "Gia dinh co xe day"
    return None


def _confidence_label(confidence: float) -> ConfidenceLabel:
    if confidence < 0.6:
        return "low"
    if confidence < 0.8:
        return "medium"
    return "high"


def _card_uncertainty(restaurant: Restaurant, constraints: ParsedConstraints) -> tuple[list[str], list[str]]:
    missing_info: list[str] = []
    assumptions: list[str] = []

    if not constraints.current_zone:
        missing_info.append("current_zone")
        assumptions.append("Chưa biết vị trí hiện tại nên khoảng cách chỉ dùng distance_minutes mặc định của dataset.")
    if constraints.voucher_required and not constraints.voucher_type:
        missing_info.append("voucher_type")
        assumptions.append("Chưa biết loại voucher cụ thể nên chỉ kiểm tra accept_voucher tổng quát.")
    if constraints.voucher_required and not _voucher_match(restaurant, constraints):
        missing_info.append("voucher_validation")
        assumptions.append("Voucher cần được người dùng kiểm tra lại trước khi di chuyển.")
    if constraints.dietary_needs and not set(constraints.dietary_needs).issubset(restaurant.dietary_tags):
        missing_info.append("dietary_validation")
        assumptions.append("Dietary tag chưa khớp hoàn toàn, cần kiểm tra menu thực tế.")
    if restaurant.distance_minutes > 15:
        missing_info.append("walking_distance_confirmation")
        assumptions.append("Quán khá xa, cần người dùng xác nhận nhóm có muốn đi bộ thêm không.")
    if constraints.quiet_preferred and restaurant.crowd_level >= 4:
        missing_info.append("crowd_level_now")
        assumptions.append("Độ đông hiện tại có thể khác dataset, nên cần kiểm tra tại thời điểm đi.")

    return missing_info, assumptions


def _score_restaurant(restaurant: Restaurant, constraints: ParsedConstraints) -> tuple[float, list[str], list[str]]:
    score = 35.0
    reasons: list[str] = []
    trade_offs: list[str] = []

    if _voucher_match(restaurant, constraints):
        score += 25
        if constraints.voucher_required:
            reasons.append("Khớp voucher yêu cầu")
    elif constraints.voucher_required:
        score -= 20
        trade_offs.append("Có thể không dùng được voucher tại điểm này")

    cuisine_matches = set(constraints.preferred_cuisines).intersection(restaurant.cuisine_types)
    if cuisine_matches:
        score += 20
        reasons.append("Có món phù hợp: " + ", ".join(sorted(cuisine_matches)))

    if constraints.has_kids and restaurant.group_suitability.kids >= 4:
        score += 15
        reasons.append("Phù hợp gia đình có trẻ em")
    if constraints.has_elderly and restaurant.group_suitability.elderly >= 4:
        score += 15
        reasons.append("Dễ chịu hơn cho người lớn tuổi")

    if (not constraints.needs_stroller or restaurant.stroller_accessible) and (
        not constraints.needs_wheelchair or restaurant.wheelchair_accessible
    ):
        score += 10
        if constraints.needs_stroller or constraints.needs_wheelchair:
            reasons.append("Đáp ứng nhu cầu xe đẩy/xe lăn")

    if constraints.quiet_preferred and restaurant.quiet_level >= 4:
        score += 10
        reasons.append("Không gian tương đối yên tĩnh")
    if restaurant.distance_minutes <= 8:
        score += 10
        reasons.append("Khoảng cách đi bộ ngắn")
    elif restaurant.distance_minutes > 15:
        score -= 10
        trade_offs.append("Đi bộ khá xa")

    if constraints.budget_per_person:
        if restaurant.avg_price_vnd <= constraints.budget_per_person:
            score += 10
            reasons.append("Nằm trong ngân sách")
        elif restaurant.avg_price_vnd <= constraints.budget_per_person * 1.3:
            trade_offs.append("Vượt ngân sách nhẹ nhưng còn trong biên linh hoạt")
    if constraints.quiet_preferred and restaurant.crowd_level >= 4:
        score -= 10
        trade_offs.append("Có thể đông/ồn vào giờ cao điểm")

    if not reasons:
        reasons.append("Cân bằng tốt giữa vị trí, giá và nhu cầu nhóm")
    return max(score, 0), reasons, trade_offs


def rank_restaurants_stub(
    restaurants: list[Restaurant], constraints: ParsedConstraints
) -> tuple[list[RecommendationCard], list[str]]:
    """Rank restaurants with transparent heuristic scoring and return Top 3."""
    strict_candidates = [item for item in restaurants if _passes_hard_filters(item, constraints)]

    if constraints.voucher_required:
        voucher_candidates = [item for item in strict_candidates if item.accept_voucher]
        if not voucher_candidates:
            return [], FALLBACK_SUGGESTIONS
        candidates = voucher_candidates if len(voucher_candidates) >= 3 else strict_candidates
    else:
        candidates = strict_candidates

    if not candidates:
        return [], FALLBACK_SUGGESTIONS

    scored = []
    for restaurant in candidates:
        score, reasons, trade_offs = _score_restaurant(restaurant, constraints)
        scored.append((score, restaurant, reasons, trade_offs))

    scored.sort(key=lambda item: item[0], reverse=True)
    recommendations: list[RecommendationCard] = []
    for rank, (score, restaurant, reasons, trade_offs) in enumerate(scored[:3], start=1):
        missing_info, assumptions = _card_uncertainty(restaurant, constraints)
        confidence = max(0.5, min(0.95, constraints.confidence + score / 500))
        if missing_info:
            confidence = min(confidence, 0.79)
        recommendations.append(
            RecommendationCard(
                restaurant_id=restaurant.id,
                name=restaurant.name,
                fit_score=round(score, 2),
                rank=rank,
                zone=restaurant.zone,
                brand_area=restaurant.brand_area,
                distance_text=restaurant.distance_text,
                avg_price_vnd=restaurant.avg_price_vnd,
                accept_voucher=restaurant.accept_voucher,
                voucher_match=_voucher_match(restaurant, constraints),
                reasons=reasons,
                trade_offs=trade_offs,
                least_satisfied_person=_least_satisfied_person(restaurant, constraints),
                confidence=confidence,
                confidence_label=_confidence_label(confidence),
                missing_info=missing_info,
                assumptions=assumptions,
                source_status=restaurant.source_status,
            )
        )

    return recommendations, []
