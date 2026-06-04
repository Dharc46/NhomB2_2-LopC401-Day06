from src.data_loader import get_dataset_summary, load_restaurants


def test_dataset_loads_with_minimum_size():
    restaurants = load_restaurants()

    assert len(restaurants) >= 35


def test_restaurant_ids_are_unique():
    restaurants = load_restaurants()
    ids = [restaurant.id for restaurant in restaurants]

    assert len(ids) == len(set(ids))


def test_dataset_has_required_business_coverage():
    restaurants = load_restaurants()

    assert sum(1 for item in restaurants if item.accept_voucher) >= 8
    assert sum(1 for item in restaurants if "buffet" in item.cuisine_types) >= 5
    assert (
        sum(
            1
            for item in restaurants
            if "vegetarian" in item.dietary_tags or "non_seafood_options" in item.dietary_tags
        )
        >= 5
    )
    assert len({item.brand_area for item in restaurants}) >= 6


def test_dataset_covers_persona_and_tradeoff_cases():
    restaurants = load_restaurants()

    cheap_quick_service = [
        item
        for item in restaurants
        if item.avg_price_vnd < 100_000
        and (
            "snack" in item.cuisine_types
            or "fast_food" in item.cuisine_types
            or "Food Court" in item.zone
        )
    ]
    kid_friendly = [item for item in restaurants if item.group_suitability.kids >= 4]
    elderly_friendly = [
        item
        for item in restaurants
        if item.group_suitability.elderly >= 4 and item.quiet_level >= 3 and item.distance_minutes <= 8
    ]
    hard_tradeoffs = [
        item
        for item in restaurants
        if item.distance_minutes > 15
        or item.crowd_level >= 5
        or item.price_tier == "luxury"
        or not item.wheelchair_accessible
    ]

    assert len(cheap_quick_service) >= 6
    assert len(kid_friendly) >= 6
    assert len(elderly_friendly) >= 6
    assert len(hard_tradeoffs) >= 4


def test_dataset_summary_runs():
    restaurants = load_restaurants()
    summary = get_dataset_summary(restaurants)

    assert summary["total_count"] == len(restaurants)
    assert summary["voucher_accepted_count"] >= 8
    assert "by_brand_area" in summary
    assert "source_status_counts" in summary
