import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from lbc import Ad, Search, User
from mcp import Client
from mcp.types import CallToolResult, TextContent

from leboncoin_mcp.geocoding import CityPoint
from leboncoin_mcp.server import build_server

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / f"{name}.json").read_text())
    return data


@dataclass
class FakeLeboncoin:
    """Stands in for `lbc.Client`, answering with lbc models built from fixtures."""

    search_raw: dict[str, Any] = field(default_factory=lambda: load("search"))
    ad_raw: dict[str, Any] = field(default_factory=lambda: load("ad"))
    user_raw: dict[str, Any] = field(default_factory=lambda: load("user"))
    error: Exception | None = None
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def _answer(self, method: str, kwargs: dict[str, Any]) -> None:
        self.calls.append((method, kwargs))
        if self.error is not None:
            raise self.error

    def search(self, **kwargs: Any) -> Search:
        self._answer("search", kwargs)
        return Search._build(raw=self.search_raw, client=self)

    def get_ad(self, ad_id: str | int) -> Ad:
        self._answer("get_ad", {"ad_id": ad_id})
        return Ad._build(raw=self.ad_raw, client=self)

    def get_user(self, user_id: str) -> User:
        self._answer("get_user", {"user_id": user_id})
        return User._build(user_data=self.user_raw, pro_data=None)

    @property
    def last_search(self) -> dict[str, Any]:
        return next(kw for method, kw in reversed(self.calls) if method == "search")


@dataclass
class FakeGeocoder:
    points: dict[str, CityPoint] = field(default_factory=dict)

    async def locate(self, name: str, postcode: str | None = None) -> CityPoint:
        return self.points[name]


@pytest.fixture
def leboncoin() -> FakeLeboncoin:
    return FakeLeboncoin()


@pytest.fixture
def geocoder() -> FakeGeocoder:
    return FakeGeocoder()


Call = Callable[[str, dict[str, Any]], Awaitable[CallToolResult]]


@pytest.fixture
def call(leboncoin: FakeLeboncoin, geocoder: FakeGeocoder) -> Call:
    """Calls a tool through the MCP protocol, one session per call.

    A session opened in a fixture would be closed from another task than the
    test's, which anyio refuses.
    """

    async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
        async with Client(build_server(leboncoin, geocoder)) as client:
            return await client.call_tool(name, arguments)

    return call_tool


def error_text(result: CallToolResult) -> str:
    assert result.is_error
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text
