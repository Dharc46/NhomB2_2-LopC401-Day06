"""Preference parser for Vietnamese resort dining requests."""

import re
import unicodedata

from src.constraint_classifier import classify_constraints
from src.schemas import ParsedConstraints, RecommendationRequest


def _repair_mojibake(text: str) -> str:
    """Best-effort repair for UTF-8 text accidentally read as latin-1."""
    if not any(marker in text for marker in ("Ã", "Ä", "á", "Æ")):
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text
    return repaired if len(repaired) <= len(text) + 8 else text


def normalize_text(text: str) -> str:
    """Lowercase and strip accents so simple rules handle Vietnamese consistently."""
    text = _repair_mojibake(text).lower()
    text = text.replace("đ", "d")
    value = unicodedata.normalize("NFKD", text)
    return "".join(char for char in value if not unicodedata.combining(char))


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(normalize_text(phrase) in text for phrase in phrases)


def _extract_budget(text: str) -> int | None:
    budget_patterns = [
        r"(?:duoi|toi da|khoang|tam|budget|ngan sach)?\s*(\d{2,4})\s*k\b",
        r"(\d{1,3}(?:[.,]\d{3})+)",
        r"(\d{5,7})",
    ]
    for pattern in budget_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        raw_value = match.group(1).replace(".", "").replace(",", "")
        amount = int(raw_value)
        if match.group(0).strip().endswith("k"):
            amount *= 1000
        if 10_000 <= amount <= 2_000_000:
            return amount
    return None


def _extract_party_size(text: str) -> int | None:
    patterns = [
        r"(?:nhom|doan|gia dinh)?\s*(\d{1,2})\s*(?:nguoi|khach|ban)",
        r"(\d{1,2})\s*(?:adult|nguoi lon)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def _extract_max_distance(text: str) -> int | None:
    match = re.search(r"(?:duoi|toi da|trong|khong qua)\s*(\d{1,2})\s*phut", text)
    if match:
        return int(match.group(1))
    if _contains_any(text, ["gan", "gan nhat", "khong di xa", "it di bo"]):
        return 8
    return None


def _extract_zone(text: str) -> str | None:
    zone_rules = {
        "sảnh chính": ["sanh chinh", "lobby", "sanh resort"],
        "cổng chính": ["cong chinh", "cong vao"],
        "harbour": ["harbour", "ben cang"],
        "food court": ["food court", "khu food court"],
        "water park": ["water park", "cong vien nuoc"],
        "resort": ["resort", "vinpearl"],
    }
    for zone, phrases in zone_rules.items():
        if _contains_any(text, phrases):
            return zone
    return None


def _extract_voucher_type(text: str) -> str | None:
    if _contains_any(text, ["buffet"]):
        return "buffet"
    if _contains_any(text, ["meal credit", "credit an uong", "tin dung an uong"]):
        return "meal_credit"
    if _contains_any(text, ["combo"]):
        return "combo"
    if _contains_any(text, ["discount", "giam gia"]):
        return "discount"
    return None


def _extract_cuisines(text: str) -> list[str]:
    cuisine_rules = {
        "pizza": ["pizza"],
        "vietnamese": ["mon viet", "do viet", "com", "pho", "bun", "cao lau"],
        "buffet": ["buffet"],
        "seafood": ["hai san"],
        "snack": ["snack", "an nhe", "kiosk"],
        "fast_food": ["ga ran", "burger", "fast food"],
    }
    cuisines: list[str] = []
    for cuisine, phrases in cuisine_rules.items():
        if _contains_any(text, phrases):
            cuisines.append(cuisine)
    if "non_seafood_options" in _extract_dietary_needs(text):
        cuisines = [item for item in cuisines if item != "seafood"]
    return cuisines


def _extract_dietary_needs(text: str) -> list[str]:
    dietary: list[str] = []
    if _contains_any(text, ["khong hai san", "di ung hai san"]):
        dietary.append("non_seafood_options")
    if _contains_any(text, ["an chay", "mon chay", "vegetarian"]):
        dietary.append("vegetarian")
    if _contains_any(text, ["halal"]):
        dietary.append("halal_friendly")
    return dietary


def parse_preference_text(request: RecommendationRequest | str) -> ParsedConstraints:
    """Parse free text and request hints into a structured constraint object."""
    if isinstance(request, str):
        request = RecommendationRequest(user_text=request)

    combined = " ".join(
        part for part in [request.user_text, request.correction or ""] if part
    )
    text = normalize_text(combined)

    dietary_needs = _extract_dietary_needs(text)
    voucher_type = request.voucher_type or _extract_voucher_type(text)
    voucher_required = bool(voucher_type) or _contains_any(
        text, ["voucher", "combo", "meal credit", "giam gia"]
    )

    has_kids = _contains_any(text, ["tre", "con", "be", "em be", "kids"])
    has_elderly = _contains_any(
        text, ["ong", "ba", "nguoi lon tuoi", "nguoi gia", "elderly"]
    )
    needs_stroller = _contains_any(text, ["xe day", "stroller"])
    needs_wheelchair = _contains_any(text, ["xe lan", "wheelchair"])
    quiet_preferred = _contains_any(
        text, ["yen tinh", "khong on", "it on", "quiet", "on ao"]
    )

    party_size = request.party_size or _extract_party_size(text)
    current_zone = request.current_zone or _extract_zone(text)
    preferred_cuisines = _extract_cuisines(text)
    budget = _extract_budget(text)
    max_distance = _extract_max_distance(text)

    confidence = 0.35
    if current_zone:
        confidence += 0.18
    if party_size:
        confidence += 0.12
    if preferred_cuisines or dietary_needs:
        confidence += 0.12
    if budget:
        confidence += 0.08
    if voucher_required and voucher_type:
        confidence += 0.12
    elif voucher_required and not voucher_type:
        confidence -= 0.08
    if has_kids or has_elderly or needs_stroller or needs_wheelchair:
        confidence += 0.08
    if request.correction:
        confidence += 0.05

    parsed = ParsedConstraints(
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
        max_distance_minutes=max_distance,
        confidence=max(0.05, min(confidence, 0.95)),
    )
    return classify_constraints(parsed)


def parse_user_text(request: RecommendationRequest) -> ParsedConstraints | str:
    """Try LLM parser first, fall back to regex.

    Returns ParsedConstraints on success, or "off_topic" if input is not dining-related.
    """
    from src.llm_parser import parse_with_llm

    result = parse_with_llm(request)
    if result == "off_topic":
        return "off_topic"
    if result is not None:
        return result

    return parse_preference_text(request)
