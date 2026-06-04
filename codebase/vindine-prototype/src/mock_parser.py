"""Rule-based temporary parser for Vietnamese group dining requests."""

import re
import unicodedata

from src.schemas import ParsedConstraints, RecommendationRequest


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.lower().replace("đ", "d"))
    return "".join(char for char in value if not unicodedata.combining(char))


def _contains_any(text: str, phrases: list[str]) -> bool:
    normalized_phrases = [_normalize(phrase) for phrase in phrases]
    return any(phrase in text for phrase in normalized_phrases)


def _extract_budget(text: str) -> int | None:
    patterns = [
        r"(\d{2,4})\s*k\b",
        r"(\d{1,3}(?:[.,]\d{3})+)",
        r"(\d{5,7})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        raw_value = match.group(1).replace(".", "").replace(",", "")
        amount = int(raw_value)
        if pattern.endswith(r"k\b"):
            amount *= 1000
        if 20_000 <= amount <= 2_000_000:
            return amount
    return None


def _extract_party_size(text: str) -> int | None:
    match = re.search(r"(?:nhom|doan|gia dinh)?\s*(\d{1,2})\s*(?:nguoi|khach|ban)", text)
    if match:
        return int(match.group(1))
    return None


def _extract_max_distance(text: str) -> int | None:
    match = re.search(r"(?:duoi|toi da|trong)\s*(\d{1,2})\s*phut", text)
    if match:
        return int(match.group(1))
    if _contains_any(text, ["gan", "gan nhat", "khong di xa"]):
        return 8
    return None


def parse_user_text_stub(request: RecommendationRequest) -> ParsedConstraints:
    """Parse a Vietnamese natural-language request with lightweight rules."""
    combined = " ".join(part for part in [request.user_text, request.correction or ""] if part)
    text = _normalize(combined)

    preferred_cuisines: list[str] = []
    dietary_needs: list[str] = []
    hard_constraints: list[str] = []
    soft_preferences: list[str] = []

    if "khong hai san" in text:
        dietary_needs.append("non_seafood_options")
        hard_constraints.append("non_seafood_options")
    elif "hai san" in text:
        preferred_cuisines.append("seafood")

    cuisine_rules = {
        "pizza": ["pizza"],
        "vietnamese": ["mon viet", "do viet", "com", "pho", "bun", "cao lau"],
        "buffet": ["buffet"],
    }
    for cuisine, phrases in cuisine_rules.items():
        if _contains_any(text, phrases) and cuisine not in preferred_cuisines:
            preferred_cuisines.append(cuisine)

    if "chay" in text and "vegetarian" not in dietary_needs:
        dietary_needs.append("vegetarian")
        hard_constraints.append("vegetarian")

    has_kids = _contains_any(text, ["tre", "con", "be"])
    has_elderly = _contains_any(text, ["ong", "ba", "nguoi lon tuoi", "nguoi gia"])
    needs_stroller = "xe day" in text
    needs_wheelchair = "xe lan" in text
    voucher_required = _contains_any(text, ["voucher", "combo", "buffet"]) or bool(request.voucher_type)
    quiet_preferred = _contains_any(text, ["yen tinh", "khong on", "it on"])

    if has_kids:
        soft_preferences.append("kids")
    if has_elderly:
        soft_preferences.append("elderly")
    if needs_stroller:
        hard_constraints.append("stroller_accessible")
    if needs_wheelchair:
        hard_constraints.append("wheelchair_accessible")
    if quiet_preferred:
        soft_preferences.append("quiet")
    if voucher_required:
        soft_preferences.append("voucher")

    budget = _extract_budget(text)
    if budget:
        hard_constraints.append("budget")

    current_zone = request.current_zone
    if not current_zone:
        zone_markers = ["sanh chinh", "cong chinh", "resort", "harbour", "food court", "water park"]
        current_zone = next((marker for marker in zone_markers if marker in text), None)

    party_size = request.party_size or _extract_party_size(text)
    voucher_type = request.voucher_type
    for candidate in ["buffet", "combo", "meal_credit", "discount"]:
        if candidate in text:
            voucher_type = candidate
            break

    confidence = 0.62
    if current_zone:
        confidence += 0.12
    if party_size:
        confidence += 0.08
    if voucher_required and voucher_type:
        confidence += 0.08
    if preferred_cuisines or dietary_needs:
        confidence += 0.05
    if not current_zone:
        confidence = min(confidence, 0.55)

    return ParsedConstraints(
        party_size=party_size,
        current_zone=current_zone,
        has_kids=has_kids,
        has_elderly=has_elderly,
        needs_stroller=needs_stroller,
        needs_wheelchair=needs_wheelchair,
        budget_per_person=budget,
        voucher_required=voucher_required,
        voucher_type=voucher_type,
        preferred_cuisines=preferred_cuisines,
        dietary_needs=dietary_needs,
        quiet_preferred=quiet_preferred,
        max_distance_minutes=_extract_max_distance(text),
        hard_constraints=hard_constraints,
        soft_preferences=soft_preferences,
        confidence=min(confidence, 0.9),
    )
