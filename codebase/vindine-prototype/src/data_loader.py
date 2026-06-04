"""Dataset loading and summary helpers."""

from collections import Counter
from json import JSONDecodeError
import json
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from src.schemas import Restaurant


def load_restaurants(path: str = "data/vin_restaurants.json") -> list[Restaurant]:
    """Load and validate restaurant records from the JSON dataset."""
    dataset_path = Path(path)
    if not dataset_path.is_absolute():
        dataset_path = Path.cwd() / dataset_path

    if not dataset_path.exists():
        raise FileNotFoundError(f"Restaurant dataset not found: {dataset_path}")

    try:
        raw_data = json.loads(dataset_path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise ValueError(
            f"Restaurant dataset contains invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(raw_data, list):
        raise ValueError("Restaurant dataset must be a JSON array")

    restaurants: list[Restaurant] = []
    for index, record in enumerate(raw_data):
        try:
            restaurants.append(Restaurant.model_validate(record))
        except ValidationError as exc:
            record_id = record.get("id", f"index-{index}") if isinstance(record, dict) else f"index-{index}"
            raise ValueError(f"Invalid restaurant record {record_id}: {exc}") from exc

    ids = [restaurant.id for restaurant in restaurants]
    duplicate_ids = sorted({item for item in ids if ids.count(item) > 1})
    if duplicate_ids:
        raise ValueError(f"Duplicate restaurant ids found: {', '.join(duplicate_ids)}")

    return restaurants


def get_dataset_summary(restaurants: Iterable[Restaurant]) -> dict:
    """Return simple aggregate counts used by health checks and demos."""
    items = list(restaurants)
    cuisine_counts: Counter[str] = Counter()
    for restaurant in items:
        cuisine_counts.update(restaurant.cuisine_types)

    return {
        "total_count": len(items),
        "by_brand_area": dict(Counter(item.brand_area for item in items)),
        "voucher_accepted_count": sum(1 for item in items if item.accept_voucher),
        "price_tiers": dict(Counter(item.price_tier for item in items)),
        "cuisine_types": dict(cuisine_counts),
        "accessibility_counts": {
            "stroller_accessible": sum(1 for item in items if item.stroller_accessible),
            "wheelchair_accessible": sum(1 for item in items if item.wheelchair_accessible),
            "indoor": sum(1 for item in items if item.indoor),
            "outdoor": sum(1 for item in items if item.outdoor),
        },
        "source_status_counts": dict(Counter(item.source_status for item in items)),
    }
