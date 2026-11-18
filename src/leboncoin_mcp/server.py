import re
from collections.abc import Callable
from typing import Annotated, Any, Literal, Protocol

import anyio
from lbc import Ad, AdType, City, Department, OwnerType, Region, Search, Sort, User
from lbc.exceptions import DatadomeError, LBCError, NotFoundError
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from leboncoin_mcp import names
from leboncoin_mcp.geocoding import CityPoint

# lbc only takes closed price ranges.
NO_PRICE_LIMIT = 1_000_000_000

type SortName = Literal["relevance", "newest", "cheapest", "most_expensive"]
type SellerTypeName = Literal["all", "private", "pro"]

SORTS: dict[SortName, Sort] = {
    "relevance": Sort.RELEVANCE,
    "newest": Sort.NEWEST,
    "cheapest": Sort.CHEAPEST,
    "most_expensive": Sort.EXPENSIVE,
}
SELLER_TYPES: dict[SellerTypeName, OwnerType] = {
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
    city: str | None
    zipcode: str | None
    department: str | None
    published_at: str
    seller_type: str
    shippable: bool
    url: str


class SearchResult(BaseModel):
    total: int | None = Field(description="How many ads match, on every page.")
    page: int
    has_next_page: bool
    ads: list[AdSummary]


class SellerReference(BaseModel):
    id: str
    name: str
    type: str


class FullAd(AdSummary):
    description: str
    category: str
    attributes: dict[str, str] = Field(
        description="Facts specific to the ad's category, such as mileage or size."
    )
    images: list[str]
    seller: SellerReference


class Rating(BaseModel):
    score: float = Field(description="Average review score out of 5.")
    reviews: int


class Seller(BaseModel):
    id: str
    name: str
    type: str
    rating: Rating | None
    reply_rate: int | None = Field(description="Share of messages answered, in %.")
    reply_minutes: int | None
    badges: list[str]
    registered_at: str | None
    last_activity: str | None
    total_ads: int | None


AD_ID = re.compile(r"(?:^|/)(\d+)(?:\.htm)?/?(?:[?#].*)?$")


def _ad_id(ad: str) -> str:
    found = AD_ID.search(ad.strip())
    if found is None:
        raise ToolError(f"{ad!r} is not an ad id or an ad URL.")
    return found.group(1)


async def _call_leboncoin[T](request: Callable[[], T], missing: str) -> T:
    """Asks Leboncoin, telling a block apart from content that does not exist."""
    try:
        return await anyio.to_thread.run_sync(request)
    except DatadomeError as error:
        raise ToolError(
            "Blocked: Leboncoin refused to answer this server, whatever was asked. "
            "Retrying later may work; the ad or seller may well exist."
        ) from error
    except NotFoundError as error:
        raise ToolError(missing) from error
    except LBCError as error:
        raise ToolError(f"Leboncoin did not answer: {error}") from error


def _full_ad(ad: Ad) -> FullAd:
    owner = ad.raw.get("owner", {})
    return FullAd(
        **_summary(ad).model_dump(),
        description=ad.body,
        category=ad.category_name,
        attributes={
            attribute.key_label: attribute.value_label
            for attribute in ad.attributes.values()
            if attribute.generic and attribute.key_label
        },
        images=ad.images or [],
        seller=SellerReference(
            id=owner.get("user_id"), name=owner.get("name"), type=owner.get("type")
        ),
    )


def _seller(user: User) -> Seller:
    feedback = user.feedback
    rating = (
        Rating(score=round(feedback.score, 1), reviews=int(feedback.received_count))
        if feedback.overall_score
        else None
    )
    return Seller(
        id=user.id,
        name=user.name,
        type=user.account_type,
        rating=rating,
        reply_rate=user.reply.rate,
        reply_minutes=user.reply.in_minutes,
        badges=[badge.name for badge in user.badges],
        registered_at=user.registered_at,
        last_activity=user.presence.last_activity,
        total_ads=user.total_ads,
    )


def _attribute(ad: Ad, key: str) -> str | None:
    attribute = ad.attributes.get(key)
    return attribute.value if attribute else None


def _price(ad: Ad) -> float | None:
    """An ad priced at zero keeps its price, unlike an Unpriced ad."""
    cents = ad.raw.get("price_cents")
    return None if cents is None else cents / 100


def _summary(ad: Ad) -> AdSummary:
    return AdSummary(
        id=ad.id,
        title=ad.title,
        price=_price(ad),
        city=ad.location.city,
        zipcode=ad.location.zipcode,
        department=ad.location.department_name,
        published_at=ad.first_publication_date,
        seller_type=ad.raw.get("owner", {}).get("type"),
        shippable=_attribute(ad, "shippable") == "true",
        url=ad.url,
    )


def _has_next_page(search: Search, page: int, limit: int) -> bool:
    if search.max_pages is not None and page >= search.max_pages:
        return False
    return search.total is None or page * limit < search.total


def build_server(leboncoin: Leboncoin, geocoder: Geocoder) -> MCPServer:
    mcp = MCPServer("leboncoin")

    async def places(
        cities: list[CityQuery], departments: list[str], regions: list[str]
    ) -> list[City | Department | Region]:
        found: list[City | Department | Region] = []
        for city in cities:
            point = await geocoder.locate(city.name, city.postcode)
            found.append(
                City(
                    lat=point.lat,
                    lng=point.lng,
                    radius=city.radius_km * 1000,
                    city=point.name,
                )
            )
        found += [names.department(name) for name in departments]
        found += [names.region(name) for name in regions]
        return found

    @mcp.tool()
    async def search_ads(  # noqa: PLR0913, PLR0917 - each argument is a criterion
        text: str | None = None,
        category: str | None = None,
        cities: list[CityQuery] | None = None,
        departments: list[str] | None = None,
        regions: list[str] | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        seller_type: Annotated[
            SellerTypeName | None, Field(description="all by default.")
        ] = None,
        shippable_only: bool | None = None,
        sort: Annotated[SortName | None, Field(description="relevance by default.")] = (
            None
        ),
        url: str | None = Field(
            default=None,
            description="A search made on the Leboncoin site or app, with all its "
            "filters. Replaces every other criterion; only limit and page apply.",
        ),
        limit: int = Field(default=35, ge=1, le=100),
        page: int = Field(default=1, ge=1),
    ) -> SearchResult:
        """Search Leboncoin ads offered for sale.

        Places combine: an ad matches if it lies in any of the cities,
        departments or regions given. Departments take a name or a number;
        regions are the current French regions. Use get_ad for an ad's full
        description and get_seller for its seller.
        """
        criteria: dict[str, Any] = {"limit": limit, "page": page}
        if url is not None:
            given = (
                text,
                category,
                cities,
                departments,
                regions,
                price_min,
                price_max,
                seller_type,
                shippable_only,
                sort,
            )
            if any(value is not None for value in given):
                raise ToolError("A search URL replaces every other criterion.")
            criteria["url"] = url
        else:
            found = await places(cities or [], departments or [], regions or [])
            criteria |= {
                "text": text,
                "locations": found or None,
                "category": names.category(category),
                "owner_type": SELLER_TYPES[seller_type or "all"],
                "shippable": True if shippable_only else None,
                "sort": SORTS[sort or "relevance"],
                "ad_type": AdType.OFFER,
            }
            if price_min is not None or price_max is not None:
                criteria["price"] = [price_min or 0, price_max or NO_PRICE_LIMIT]
        search = await _call_leboncoin(
            lambda: leboncoin.search(**criteria), "Leboncoin found no such search."
        )
        return SearchResult(
            total=search.total,
            page=page,
            has_next_page=_has_next_page(search, page, limit),
            ads=[_summary(ad) for ad in search.ads],
        )

    @mcp.tool()
    async def get_ad(
        ad: str = Field(description="An ad id, or its URL on the Leboncoin site."),
    ) -> FullAd:
        """Get an ad's full description, category facts, photos and seller."""
        ad_id = _ad_id(ad)
        found = await _call_leboncoin(
            lambda: leboncoin.get_ad(ad_id),
            f"Unavailable ad: {ad_id} was sold, withdrawn or has expired.",
        )
        return _full_ad(found)

    @mcp.tool()
    async def get_seller(
        seller_id: str = Field(description="The seller id given by get_ad."),
    ) -> Seller:
        """Get a seller's reputation: rating, responsiveness, seniority, activity."""
        user = await _call_leboncoin(
            lambda: leboncoin.get_user(seller_id),
            f"Unknown seller: no seller has the id {seller_id!r}.",
        )
        return _seller(user)

    return mcp
