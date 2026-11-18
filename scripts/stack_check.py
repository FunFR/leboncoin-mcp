"""Checks a running server end to end over streamable HTTP.

Without --require-live, a search Leboncoin blocks still passes: the check is
then about the stack answering with a well-formed error, not about Leboncoin.
"""

import argparse
import sys

import anyio
import httpx
from mcp import Client
from mcp.types import TextContent

TOOLS = {"search_ads", "get_ad", "get_seller"}
DEADLINE_SECONDS = 120


async def wait_for(url: str) -> None:
    """Gives a freshly started container time to listen."""
    while True:
        try:
            async with httpx.AsyncClient() as http:
                await http.get(url)
            return
        except httpx.TransportError:
            await anyio.sleep(1)


async def check(url: str, require_live: bool) -> str | None:
    await wait_for(url)
    async with Client(url) as client:
        tools = {tool.name for tool in (await client.list_tools()).tools}
        if tools != TOOLS:
            return f"expected tools {sorted(TOOLS)}, got {sorted(tools)}"
        result = await client.call_tool("search_ads", {"text": "vélo", "limit": 5})
    if not result.is_error:
        ads = (result.structured_content or {}).get("ads")
        return None if ads else f"search returned no ads: {result.structured_content}"
    text = " ".join(b.text for b in result.content if isinstance(b, TextContent))
    if "Blocked:" in text and not require_live:
        print(f"Leboncoin blocked the search, the stack answered well: {text}")
        return None
    return f"search failed: {text}"


async def within_deadline(url: str, require_live: bool) -> str | None:
    try:
        with anyio.fail_after(DEADLINE_SECONDS):
            return await check(url, require_live)
    except TimeoutError:
        return f"no answer within {DEADLINE_SECONDS} seconds"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8000/mcp")
    parser.add_argument("--require-live", action="store_true")
    arguments = parser.parse_args()
    failure = anyio.run(within_deadline, arguments.url, arguments.require_live)
    if failure:
        sys.exit(f"Stack check failed: {failure}")
    print("Stack check passed.")


if __name__ == "__main__":
    main()
