import pytest
from lbc.exceptions import DatadomeError, NotFoundError, RequestTimeout

from tests.conftest import Call, FakeLeboncoin, error_text, load


async def test_get_ad_returns_the_full_ad(call: Call) -> None:
    result = await call("get_ad", {"ad": "3291258592"})

    ad = result.structured_content
    assert ad["id"] == 3291258592
    assert ad["title"] == "Vélo cargo Élé"
    assert ad["price"] == 700.0
    assert ad["category"] == "Vélos"
    assert ad["description"] == load("ad")["body"]
    assert ad["attributes"]["Type"] == "Vélo cargo"
    assert "profile_picture_url" not in ad["attributes"]
    assert ad["images"] == ["https://img.leboncoin.fr/fixture.jpg"] * 2
    assert ad["shippable"] is True
    assert ad["seller"] == {
        "id": "00000000-0000-4000-8000-000000000001",
        "name": "Vendeur A",
        "type": "private",
    }


async def test_get_ad_accepts_the_ad_url(call: Call, leboncoin: FakeLeboncoin) -> None:
    await call("get_ad", {"ad": "https://www.leboncoin.fr/ad/velos/3291258592"})

    assert leboncoin.calls == [("get_ad", {"ad_id": "3291258592"})]


async def test_get_ad_refuses_what_is_not_an_ad(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    result = await call("get_ad", {"ad": "vélo cargo"})

    assert "not an ad" in error_text(result)
    assert leboncoin.calls == []


async def test_an_unavailable_ad_is_reported_as_such(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    leboncoin.error = NotFoundError("Unable to find ad or user.")

    result = await call("get_ad", {"ad": "3291258592"})

    assert "Unavailable ad:" in error_text(result)


async def test_get_seller_returns_reputation(call: Call) -> None:
    result = await call(
        "get_seller", {"seller_id": "00000000-0000-4000-8000-000000000001"}
    )

    seller = result.structured_content
    assert seller == {
        "id": "00000000-0000-4000-8000-000000000001",
        "name": "Vendeur A",
        "type": "private",
        "rating": None,
        "reply_rate": 100,
        "reply_minutes": 30,
        "badges": ["Responsiveness3", "VerifiedPhoneNumber"],
        "registered_at": "2023-10-02",
        "last_activity": "2026-10-19T11:26:42Z",
        "total_ads": 1,
    }


async def test_get_seller_rates_out_of_five(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    leboncoin.user_raw["feedback"] = {"overall_score": 0.96, "received_count": 12}

    result = await call("get_seller", {"seller_id": "x"})

    assert result.structured_content["rating"] == {"score": 4.8, "reviews": 12}


async def test_an_unknown_seller_is_reported_as_such(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    leboncoin.error = NotFoundError("Unable to find ad or user.")

    result = await call("get_seller", {"seller_id": "x"})

    assert "Unknown seller:" in error_text(result)


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("search_ads", {}),
        ("get_ad", {"ad": "1"}),
        ("get_seller", {"seller_id": "x"}),
    ],
)
async def test_every_tool_reports_a_block_apart_from_missing_content(
    call: Call, leboncoin: FakeLeboncoin, tool: str, arguments: dict[str, str]
) -> None:
    leboncoin.error = DatadomeError("Access blocked by Datadome")

    result = await call(tool, arguments)

    assert "Blocked:" in error_text(result)


async def test_a_silent_leboncoin_is_reported(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    leboncoin.error = RequestTimeout("Request timed out.")

    result = await call("search_ads", {})

    assert "Leboncoin did not answer:" in error_text(result)
