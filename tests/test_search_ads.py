from lbc import AdType, Category, OwnerType, Sort

from tests.conftest import Call, error_text, FakeLeboncoin


async def test_search_returns_ad_summaries_and_total(call: Call) -> None:
    result = await call("search_ads", {"text": "vélo cargo"})

    assert not result.is_error
    content = result.structured_content
    assert content["total"] == 239
    first = content["ads"][0]
    assert first == {
        "id": 3291258592,
        "title": "Vélo cargo Élé",
        "price": 700.0,
        "city": "Bordeaux",
        "zipcode": "33000",
        "department": "Gironde",
        "published_at": "2026-10-19 13:28:10",
        "seller_type": "private",
        "shippable": True,
        "url": "https://www.leboncoin.fr/ad/velos/3291258592",
    }
    assert content["ads"][1]["shippable"] is False


async def test_search_passes_criteria_to_leboncoin(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    result = await call(
        "search_ads",
        {
            "text": "vélo cargo",
            "category": "velos",
            "price_min": 100,
            "price_max": 900,
            "seller_type": "private",
            "shippable_only": True,
            "sort": "cheapest",
        },
    )

    assert not result.is_error
    criteria = leboncoin.last_search
    assert criteria["text"] == "vélo cargo"
    assert criteria["category"] is Category.VEHICULES_VELOS
    assert criteria["price"] == [100, 900]
    assert criteria["owner_type"] is OwnerType.PRIVATE
    assert criteria["shippable"] is True
    assert criteria["sort"] is Sort.CHEAPEST
    assert criteria["ad_type"] is AdType.OFFER


async def test_search_leaves_unset_criteria_to_leboncoin_defaults(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    await call("search_ads", {})

    criteria = leboncoin.last_search
    assert criteria["category"] is Category.TOUTES_CATEGORIES
    assert criteria["owner_type"] is OwnerType.ALL
    assert criteria["shippable"] is None
    assert criteria["sort"] is Sort.RELEVANCE
    assert "price" not in criteria


async def test_search_suggests_close_categories_for_an_unknown_one(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    result = await call("search_ads", {"category": "vélo"})

    assert result.is_error
    message = error_text(result)
    assert "Unknown category 'vélo'" in message
    assert "Vehicules velos" in message
    assert leboncoin.calls == []


async def test_search_with_a_single_price_bound_leaves_the_other_open(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    await call("search_ads", {"price_max": 300})

    low, high = leboncoin.last_search["price"]
    assert low == 0
    assert high == 300
