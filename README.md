# Leboncoin MCP

[![GitHub Release][releases-shield]][releases]
[![Release][release-workflow-shield]][release-workflow]
[![License][license-shield]][license]

A read-only [MCP](https://modelcontextprotocol.io) server for [Leboncoin](https://www.leboncoin.fr) classified ads, so an assistant such as Claude can find items to buy and assess their sellers. It never logs into a Leboncoin account.

It builds on [`lbc`](https://github.com/etienne-hd/lbc), which speaks Leboncoin's API. Why another server rather than an existing one: [ADR 0001](docs/adr/0001-own-server-over-lbc.md).

## Tools

| Tool | What it returns |
|---|---|
| `search_ads` | One page of ads matching text, category, cities with a radius, departments, regions, price range, seller type and shipping, or a search URL copied from Leboncoin. |
| `get_ad` | An ad's full description, category facts, photos and seller, from its id or URL. |
| `get_seller` | A seller's rating, responsiveness, seniority and activity. |

Names are matched leniently (`velos`, `Vélos`, `Côtes-d'Armor`, `22`), and an unknown or ambiguous name answers with what it could mean. Cities are located through [geo.api.gouv.fr](https://geo.api.gouv.fr).

## Run it

With Docker, from a clone:

```sh
docker compose up -d
```

The server listens on `http://127.0.0.1:8000/mcp`, on the loopback interface only, since it has no authentication. Add it to Claude Code:

```sh
claude mcp add --transport http leboncoin http://127.0.0.1:8000/mcp
```

Or let the client start it over stdio, without Docker:

```sh
claude mcp add leboncoin -- uvx --from git+https://github.com/FunFR/leboncoin-mcp leboncoin-mcp
```

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` (`streamable-http` in the image) | `stdio` or `streamable-http` |
| `MCP_HOST` | `127.0.0.1` (`0.0.0.0` in the image) | Address to listen on |
| `MCP_PORT` | `8000` | Port to listen on |
| `MCP_PATH` | `/mcp` | Endpoint path |

Exposing the server beyond your machine is up to you: put access control in front of it.

## Blocks

Leboncoin protects its API against bots. When it refuses a request, tools answer `Blocked:` rather than pretend the ad or seller is missing. Blocks depend on the network the server runs from: a residential connection fares better than a datacenter. Fixes usually come with a new `lbc` release, which this project picks up and releases automatically.

## Develop

```sh
uv sync
uv run pre-commit install
uv run pytest
```

Tests run against recorded Leboncoin answers in `tests/fixtures`, never against Leboncoin. To try a change against the real service:

```sh
docker compose up -d --build
uv run python scripts/stack_check.py --require-live
```

Each merge with a `feat` or `fix` commit is released and published as `ghcr.io/funfr/leboncoin-mcp`. Maintainers can publish `pr-<number>` from a pull request by adding the `preview` label.

## License

[Apache-2.0](LICENSE)

[releases]: https://github.com/FunFR/leboncoin-mcp/releases
[releases-shield]: https://img.shields.io/github/release/FunFR/leboncoin-mcp.svg
[release-workflow]: https://github.com/FunFR/leboncoin-mcp/actions/workflows/release.yml
[release-workflow-shield]: https://github.com/FunFR/leboncoin-mcp/actions/workflows/release.yml/badge.svg
[license]: LICENSE
[license-shield]: https://img.shields.io/github/license/FunFR/leboncoin-mcp.svg
