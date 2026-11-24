FROM ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d AS uv

FROM python:3.15-slim@sha256:2c879838405817bd51e53c75ab78f613f446c448070c2d70e2e99639705bd409 AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.15-slim@sha256:2c879838405817bd51e53c75ab78f613f446c448070c2d70e2e99639705bd409
# The server never installs anything: pip only adds vulnerabilities to scan.
RUN rm -rf /usr/local/lib/python3.*/site-packages/pip* /usr/local/bin/pip* \
    && useradd --system --uid 10001 --no-create-home mcp
COPY --from=build /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH \
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000
USER mcp
EXPOSE 8000
ENTRYPOINT ["leboncoin-mcp"]
