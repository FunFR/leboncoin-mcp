import json
from typing import Any

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from leboncoin_mcp.geocoding import CityPoint, GeoApiGeocoder


def commune(name: str, lng: float, lat: float, postcodes: list[str], dept: str) -> Any:
    return {
        "nom": name,
        "centre": {"type": "Point", "coordinates": [lng, lat]},
        "codesPostaux": postcodes,
        "codeDepartement": dept,
    }


BORDEAUX = commune("Bordeaux", -0.5848, 44.8624, ["33000", "33100"], "33")
BORDEAUX_SAINT_CLAIR = commune("Bordeaux-Saint-Clair", 0.2445, 49.6953, ["76790"], "76")
SAINT_MARTINIEN = commune("Saint-Martinien", 2.442, 46.3328, ["03380"], "03")
SAINT_MARTIN_65 = commune("Saint-Martin", 0.0667, 43.1683, ["65360"], "65")
SAINT_MARTIN_32 = commune("Saint-Martin", 0.3758, 43.5096, ["32300"], "32")


def geocoder(answer: list[Any], seen: list[httpx.Request]) -> GeoApiGeocoder:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=json.dumps(answer))

    return GeoApiGeocoder(httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_a_city_is_located_at_its_centre() -> None:
    seen: list[httpx.Request] = []

    point = await geocoder([BORDEAUX, BORDEAUX_SAINT_CLAIR], seen).locate("bordeaux")

    assert point == CityPoint("Bordeaux", 44.8624, -0.5848)
    assert seen[0].url.params["nom"] == "bordeaux"


async def test_homonyms_without_postcode_are_listed() -> None:
    answer = [SAINT_MARTINIEN, SAINT_MARTIN_65, SAINT_MARTIN_32]

    with pytest.raises(ToolError) as raised:
        await geocoder(answer, []).locate("Saint-Martin")

    message = str(raised.value)
    assert "Saint-Martin (65360)" in message
    assert "Saint-Martin (32300)" in message
    assert "Saint-Martinien" not in message


async def test_a_postcode_picks_the_homonym() -> None:
    seen: list[httpx.Request] = []

    point = await geocoder([SAINT_MARTIN_32], seen).locate("Saint-Martin", "32300")

    assert point == CityPoint("Saint-Martin", 43.5096, 0.3758)
    assert seen[0].url.params["codePostal"] == "32300"


async def test_a_partial_name_suggests_the_cities_found() -> None:
    with pytest.raises(ToolError) as raised:
        await geocoder([SAINT_MARTINIEN], []).locate("Saint-Martini")

    assert "Saint-Martinien (03380)" in str(raised.value)


async def test_an_unknown_city_is_reported() -> None:
    with pytest.raises(ToolError) as raised:
        await geocoder([], []).locate("Zzzzqx")

    assert "Unknown city 'Zzzzqx'" in str(raised.value)


# A 302 to sorry.data.gouv.fr is how the service answered during its 2026-11-18 outage.
@pytest.mark.parametrize(
    "outage",
    [
        httpx.Response(503),
        httpx.Response(302, headers={"Location": "http://sorry.data.gouv.fr"}),
    ],
    ids=["unavailable", "redirected"],
)
async def test_a_geocoder_outage_points_to_departments(outage: httpx.Response) -> None:
    failing = GeoApiGeocoder(
        httpx.AsyncClient(transport=httpx.MockTransport(lambda _: outage))
    )

    with pytest.raises(ToolError) as raised:
        await failing.locate("Lyon")

    message = str(raised.value)
    assert message.startswith(
        "Could not locate 'Lyon': the city service failed. "
        "Retry without cities, using departments instead."
    )
