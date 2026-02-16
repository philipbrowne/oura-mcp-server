# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run a single test file
pytest tests/test_api_client.py

# Run tests matching a pattern
pytest -k "test_pagination"

# Linting and formatting (uses Ruff)
ruff check .
ruff check --fix .
ruff format .

# Run the MCP server (stdio)
oura-mcp

# Test with MCP Inspector
npx @modelcontextprotocol/inspector oura-mcp
```

## Architecture Overview

This is a Model Context Protocol (MCP) server that provides Claude with access to the Oura Ring health data API v2. The architecture follows a clean layered design:

```
server.py (MCP tools) → api_client.py → Oura API (Bearer token auth)
                              ↓
                         models.py (Pydantic)
```

### Request Flow

1. **server.py**: Defines MCP tools using FastMCP decorators (`@mcp.tool()`). Each tool wraps an API client method and formats responses for Claude consumption. Every tool returns a string with try/except for friendly error messages.

2. **api_client.py**: `OuraClient` handles all HTTP communication with the Oura API v2. Uses `httpx.AsyncClient` for async GET requests. Key features:
   - Bearer token authentication via `Authorization` header
   - Automatic token refresh on 401 (one retry)
   - Cursor-based pagination via `_get_paginated()` following `next_token`
   - `on_token_refresh` callback to persist new tokens

3. **oauth_flow.py**: `OAuthFlowManager` implements OAuth2 Authorization Code flow (2 steps, simpler than OAuth1). Uses OOB redirect URI for CLI usage.

4. **token_store.py**: `TokenStore` (file-based) and `EnvTokenStore` (env vars for cloud). Simpler than FatSecret — no request token step, just access + refresh tokens.

5. **config.py**: Uses `pydantic-settings` to load environment variables with `OURA_` prefix. Required: `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET`.

6. **models.py**: Pydantic models for type-safe API response parsing. All data fields optional (`| None = None`) since Oura may omit based on ring generation/subscription.

### Key Differences from FatSecret

- **OAuth2** (not OAuth1) — no `auth.py` signing module, just Bearer token header
- **GET requests** (not POST) — Oura API is read-only
- **Cursor pagination** (`next_token`) vs page-number pagination
- **Simpler token flow** — 2 steps (URL + code exchange) vs 3 (request token + URL + verifier)

### Server Lifecycle

The server uses FastMCP's lifespan context manager to:
- Initialize settings, token store, OAuth flow manager, and API client on startup
- Detect cloud environment (Railway/Render) to use `EnvTokenStore`
- Close HTTP clients on shutdown

### Exception Hierarchy

All exceptions inherit from `OuraError`:
- `AuthenticationError` → `TokenExpiredError`, `TokenRefreshError`
- `APIError` (with status_code) → `RateLimitError`, `DataNotFoundError`
- `ConfigurationError`, `OAuthFlowError`, `UserNotAuthenticatedError`

### Testing Patterns

Tests use `respx` to mock httpx responses. Fixtures in `conftest.py` provide:
- `settings`: Test credentials
- `mock_*_response`: Sample API responses for various endpoints
- `token`: Test OAuth2 token

The `asyncio_mode = "auto"` pytest setting enables automatic async test handling.
