from lbc import City, Department, Region

from leboncoin_mcp.geocoding import CityPoint
from tests.conftest import Call, FakeGeocoder, FakeLeboncoin, error_text


async def test_departments_are_named_by_name_or_number(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    await call("search_ads", {"departments": ["Gironde", "17", "côtes d'armor"]})

    assert leboncoin.last_search["locations"] == [
        Department.GIRONDE,
        Department.CHARENTE_MARITIME,
        Department.COTES_DARMOR,
    ]


async def test_an_overseas_department_searches_its_region(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    await call("search_ads", {"departments": ["974"]})

    assert leboncoin.last_search["locations"] == [Region.REUNION]


async def test_a_corsican_department_points_to_the_corse_region(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    result = await call("search_ads", {"departments": ["2A"]})

    assert result.is_error
    assert "Corse" in error_text(result)
    assert leboncoin.calls == []


async def test_regions_are_the_current_ones(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    await call(
        "search_ads",
        {"regions": ["Nouvelle-Aquitaine", "Provence-Alpes-Côte d'Azur"]},
    )

    assert leboncoin.last_search["locations"] == [
        Region.NOUVELLE_AQUITAINE,
        Region.PROVENCE_ALPES_COTE_DAZUR,
    ]


async def test_a_former_region_is_refused(call: Call, leboncoin: FakeLeboncoin) -> None:
    result = await call("search_ads", {"regions": ["Aquitaine"]})

    assert result.is_error
    assert "Nouvelle aquitaine" in error_text(result)


async def test_cities_are_searched_within_their_radius(
    call: Call, leboncoin: FakeLeboncoin, geocoder: FakeGeocoder
) -> None:
    geocoder.points["Bordeaux"] = CityPoint("Bordeaux", 44.837, -0.579)

    await call(
        "search_ads",
        {"cities": [{"name": "Bordeaux", "radius_km": 25}], "regions": ["Bretagne"]},
    )

    assert leboncoin.last_search["locations"] == [
        City(lat=44.837, lng=-0.579, radius=25_000, city="Bordeaux"),
        Region.BRETAGNE,
    ]


async def test_a_city_radius_defaults_to_ten_kilometres(
    call: Call, leboncoin: FakeLeboncoin, geocoder: FakeGeocoder
) -> None:
    geocoder.points["Lyon"] = CityPoint("Lyon", 45.76, 4.83)

    await call("search_ads", {"cities": [{"name": "Lyon"}]})

    assert leboncoin.last_search["locations"][0].radius == 10_000


async def test_no_place_searches_everywhere(
    call: Call, leboncoin: FakeLeboncoin
) -> None:
    await call("search_ads", {})

    assert leboncoin.last_search["locations"] is None
