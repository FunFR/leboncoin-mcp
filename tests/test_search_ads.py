from lbc import AdType, Category, OwnerType, Sort

from tests.conftest import Call, FakeLeboncoin, error_text


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
            "category": "loisirs velos",
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
    assert criteria["category"] is Category.LOISIRS_VELOS
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


async def test_search_returns_one_page_and_tells_whether_more_exist(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    result = await call("search_ads", {"limit": 50, "page": 2})

    assert leboncoin.last_search["limit"] == 50
    assert leboncoin.last_search["page"] == 2
    assert result.structured_content["page"] == 2
    assert result.structured_content["has_next_page"] is True


async def test_search_has_no_next_page_past_the_total(call: Call) -> None:
    result = await call("search_ads", {"limit": 35, "page": 7})

    assert result.structured_content["has_next_page"] is False


async def test_search_returns_35_ads_by_default_and_100_at_most(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    await call("search_ads", {})
    assert leboncoin.last_search["limit"] == 35

    result = await call("search_ads", {"limit": 101})
    assert result.is_error


async def test_search_url_replaces_criteria(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    url = "https://www.leboncoin.fr/recherche?category=55&text=cargo"

    await call("search_ads", {"url": url, "page": 3})

    assert leboncoin.last_search == {"url": url, "limit": 35, "page": 3}


async def test_search_url_cannot_be_mixed_with_criteria(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    result = await call(
        "search_ads",
        {"url": "https://www.leboncoin.fr/recherche?text=cargo", "text": "vélo"},
    )

    assert "replaces" in error_text(result)
    assert leboncoin.calls == []


async def test_search_has_no_next_page_past_what_leboncoin_serves(call: Call) -> None:
    result = await call("search_ads", {"limit": 1, "page": 80})

    assert result.structured_content["has_next_page"] is False


async def test_search_lists_the_categories_an_ambiguous_name_could_mean(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    result = await call("search_ads", {"category": "vélos"})

    message = error_text(result)
    assert "Vehicules velos" in message
    assert "Loisirs velos" in message
    assert leboncoin.calls == []


async def test_search_takes_a_category_by_its_name_within_its_parent(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    await call("search_ads", {"category": "Voitures"})

    assert leboncoin.last_search["category"] is Category.VEHICULES_VOITURES


async def test_an_ad_missing_place_details_does_not_break_the_search(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    location = leboncoin.search_raw["ads"][0]["location"]
    for field in ("department_name", "city", "zipcode"):
        del location[field]

    result = await call("search_ads", {})

    first = result.structured_content["ads"][0]
    assert (first["department"], first["city"], first["zipcode"]) == (None, None, None)


async def test_an_ad_priced_at_zero_keeps_its_price(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    ads = leboncoin.search_raw["ads"]
    ads[0] |= {"price": [0], "price_cents": 0}
    del ads[1]["price"], ads[1]["price_cents"]

    result = await call("search_ads", {})

    summaries = result.structured_content["ads"]
    assert summaries[0]["price"] == 0.0
    assert summaries[1]["price"] is None
