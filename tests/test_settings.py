import pytest

from leboncoin_mcp import Settings


def test_stdio_is_the_default() -> None:
    assert Settings.from_env({}) == Settings(
        transport="stdio", host="127.0.0.1", port=8000, path="/mcp"
    )


def test_http_is_configured_from_the_environment() -> None:
    settings = Settings.from_env(
        {
            "MCP_TRANSPORT": "streamable-http",
            "MCP_HOST": "0.0.0.0",
            "MCP_PORT": "9000",
            "MCP_PATH": "/mcp/secret",
        }
    )

    assert settings == Settings(
        transport="streamable-http", host="0.0.0.0", port=9000, path="/mcp/secret"
    )


def test_an_unknown_transport_is_refused() -> None:
    with pytest.raises(ValueError, match="MCP_TRANSPORT"):
        Settings.from_env({"MCP_TRANSPORT": "sse"})
