#!/usr/bin/env python3
"""Oura MCP Server for cloud deployment (SSE transport).

Works with Railway, Render, or any platform that sets PORT env var.
Adds a /health endpoint for Railway health checks.
"""

import os

import uvicorn
from starlette.responses import PlainTextResponse
from starlette.routing import Route

# Must bind to 0.0.0.0 for cloud platforms (not localhost)
os.environ["FASTMCP_HOST"] = "0.0.0.0"

from oura_mcp.server import mcp


def health(request):
    return PlainTextResponse("ok")


def main() -> None:
    """Run the Oura MCP server with SSE transport and health check."""
    app = mcp.sse_app()

    # Add health check routes for Railway (root + /health)
    app.routes.insert(0, Route("/", health))
    app.routes.insert(1, Route("/health", health))

    port = int(os.environ.get("PORT", os.environ.get("FASTMCP_PORT", "8000")))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
