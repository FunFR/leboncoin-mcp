from typing import Any, Literal, Protocol

import anyio
from lbc import Ad, AdType, City, Department, OwnerType, Region, Search, Sort, User
from mcp.server import MCPServer
from pydantic import BaseModel, Field

from leboncoin_mcp import names
from leboncoin_mcp.geocoding import CityPoint

# lbc only takes closed price ranges.
NO_PRICE_LIMIT = 1_000_000_000

SORTS = {
    "relevance": Sort.RELEVANCE,
    "newest": Sort.NEWEST,
    "cheapest": Sort.CHEAPEST,
    "most_expensive": Sort.EXPENSIVE,
}
SELLER_TYPES = {
    "all": OwnerType.ALL,
    "private": OwnerType.PRIVATE,
    "pro": OwnerType.PRO,
}


class Leboncoin(Protocol):
    def search(self, **kwargs: Any) -> Search: ...
    def get_ad(self, ad_id: str | int) -> Ad: ...
    def get_user(self, user_id: str) -> User: ...


class Geocoder(Protocol):
    async def locate(self, name: str, postcode: str | None = None) -> CityPoint: ...


class CityQuery(BaseModel):
    name: str = Field(description="City name, such as 'Bordeaux'.")
    postcode: str | None = Field(
        default=None, description="Postcode telling homonymous cities apart."
    )
    radius_km: int = Field(default=10, ge=1, le=200)


class AdSummary(BaseModel):
    id: int
    title: str
    price: float | None
    city: str
    zipcode: str
    department: str
    published_at: str
    seller_type: str
    shippable: bool
    url: str


class SearchResult(BaseModel):
    total: int | None
    ads: list[AdSummary]


def _attribute(ad: Ad, key: str) -> str | None:
    attribute = ad.attributes.get(key)
    return attribute.value if attribute else None


def _summary(ad: Ad) -> AdSummary:
    return AdSummary(
        id=ad.id,
        title=ad.title,
        price=ad.price,
        city=ad.location.city,
        zipcode=ad.location.zipcode,
        department=ad.location.department_name,
        published_at=ad.first_publication_date,
        seller_type=ad.raw.get("owner", {}).get("type"),
        shippable=_attribute(ad, "shippable") == "true",
        url=ad.url,
    )


def build_server(leboncoin: Leboncoin, geocoder: Geocoder) -> MCPServer:
    mcp = MCPServer("leboncoin")

    @mcp.tool()
    async def search_ads(
        text: str | None = None,
        category: str | None = None,
        cities: list[CityQuery] | None = None,
        departments: list[str] | None = None,
        regions: list[str] | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        seller_type: Literal["all", "private", "pro"] = "all",
        shippable_only: bool = False,
        sort: Literal["relevance", "newest", "cheapest", "most_expensive"] = (
            "relevance"
        ),
    ) -> SearchResult:
        """Search Leboncoin ads offered for sale."""
        locations: list[City | Department | Region] = []
        for city in cities or []:
            point = await geocoder.locate(city.name, city.postcode)
            locations.append(
                City(
                    lat=point.lat,
                    lng=point.lng,
                    radius=city.radius_km * 1000,
                    city=point.name,
                )
            )
        locations += [names.department(name) for name in departments or []]
        locations += [names.region(name) for name in regions or []]
        criteria: dict[str, Any] = {
            "text": text,
            "locations": locations or None,
            "category": names.category(category),
            "owner_type": SELLER_TYPES[seller_type],
            "shippable": True if shippable_only else None,
            "sort": SORTS[sort],
            "ad_type": AdType.OFFER,
        }
        if price_min is not None or price_max is not None:
            criteria["price"] = [price_min or 0, price_max or NO_PRICE_LIMIT]
        search = await anyio.to_thread.run_sync(lambda: leboncoin.search(**criteria))
        return SearchResult(total=search.total, ads=[_summary(ad) for ad in search.ads])

    return mcp
