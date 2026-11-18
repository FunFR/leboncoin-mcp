"""Locates French cities through the State's public API, geo.api.gouv.fr."""

from dataclasses import dataclass
from typing import Any

import httpx
from mcp.server.mcpserver.exceptions import ToolError

from leboncoin_mcp.names import same_name

COMMUNES = "https://geo.api.gouv.fr/communes"


@dataclass(frozen=True)
class CityPoint:
    name: str
    lat: float
    lng: float


def _label(commune: dict[str, Any]) -> str:
    return f"{commune['nom']} ({commune['codesPostaux'][0]})"


class GeoApiGeocoder:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def locate(self, name: str, postcode: str | None = None) -> CityPoint:
        params = {
            "nom": name,
            "fields": "nom,centre,codesPostaux",
            "boost": "population",
            "limit": "20",
        }
        if postcode:
            params["codePostal"] = postcode
        try:
            response = await self._http.get(COMMUNES, params=params)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ToolError(f"Could not locate {name!r}: {error}") from error
        found: list[dict[str, Any]] = response.json()
        exact = [commune for commune in found if same_name(commune["nom"], name)]
        if len(exact) == 1:
            longitude, latitude = exact[0]["centre"]["coordinates"]
            return CityPoint(exact[0]["nom"], latitude, longitude)
        if exact:
            homonyms = ", ".join(_label(commune) for commune in exact)
            raise ToolError(
                f"Several cities are named {name!r}: {homonyms}. "
                "Give the postcode of the one meant."
            )
        hint = ", ".join(_label(commune) for commune in found[:5])
        raise ToolError(
            f"Unknown city {name!r}." + (f" Did you mean: {hint}?" if hint else "")
        )
