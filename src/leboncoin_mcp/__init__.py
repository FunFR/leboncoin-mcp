import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, cast

import httpx
import lbc

from leboncoin_mcp.geocoding import GeoApiGeocoder
from leboncoin_mcp.server import build_server

TRANSPORTS = ("stdio", "streamable-http")


@dataclass(frozen=True)
class Settings:
    transport: Literal["stdio", "streamable-http"]
    host: str
    port: int
    path: str

    @staticmethod
    def from_env(env: Mapping[str, str]) -> Settings:
        transport = env.get("MCP_TRANSPORT", "stdio")
        if transport not in TRANSPORTS:
            raise ValueError(f"MCP_TRANSPORT must be one of {', '.join(TRANSPORTS)}.")
        return Settings(
            transport=cast(Literal["stdio", "streamable-http"], transport),
            host=env.get("MCP_HOST", "127.0.0.1"),
            port=int(env.get("MCP_PORT", "8000")),
            path=env.get("MCP_PATH", "/mcp"),
        )


def main() -> None:  # pragma: no cover - wiring exercised by the stack test
    settings = Settings.from_env(os.environ)
    server = build_server(lbc.Client(), GeoApiGeocoder(httpx.AsyncClient(timeout=10)))
    if settings.transport == "stdio":
        server.run()
    else:
        server.run(
            transport="streamable-http",
            host=settings.host,
            port=settings.port,
            streamable_http_path=settings.path,
        )
