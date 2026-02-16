#!/usr/bin/env python3
"""Local OAuth2 authentication helper.

Run this to complete the OAuth flow and get tokens for Railway deployment.
Spins up a temporary local server to catch the OAuth redirect.
"""

import asyncio
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from oura_mcp.config import get_settings
from oura_mcp.oauth_flow import OAuthFlowManager
from oura_mcp.token_store import TokenStore

REDIRECT_URI = "http://localhost:8080/callback"
captured_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global captured_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            captured_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authorization successful!</h1>"
                b"<p>You can close this tab and return to the terminal.</p>"
            )
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h1>Error: {error}</h1>".encode())

    def log_message(self, format, *args):
        pass  # Suppress request logs


async def main():
    settings = get_settings()
    token_store = TokenStore(settings.token_storage_path)
    oauth = OAuthFlowManager(settings, token_store)

    # Build auth URL with localhost redirect
    params = {
        "response_type": "code",
        "client_id": settings.client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": settings.oauth_scopes,
    }
    auth_url = f"{settings.oauth_authorize_url}?{urllib.parse.urlencode(params)}"

    # Start local server
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    print(f"\nOpening browser for Oura authorization...\n")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for authorization...")
    thread.join(timeout=120)
    server.server_close()

    if not captured_code:
        print("\nError: No authorization code received. Timed out or denied.")
        await oauth.close()
        return

    print(f"\nCode received! Exchanging for tokens...\n")

    # Exchange code — use localhost redirect URI
    import time

    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.oauth_token_url,
            data={
                "grant_type": "authorization_code",
                "code": captured_code,
                "redirect_uri": REDIRECT_URI,
                "client_id": settings.client_id,
                "client_secret": settings.client_secret,
            },
        )
        response.raise_for_status()
        token_data = response.json()

    from oura_mcp.models import OAuth2Token

    token = OAuth2Token(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_type=token_data.get("token_type", "Bearer"),
        expires_in=token_data.get("expires_in"),
        created_at=time.time(),
    )
    token_store.save_token(token)

    print("Success! Tokens saved locally.\n")
    print("Set these on Railway:\n")
    print(f"   OURA_ACCESS_TOKEN={token.access_token}")
    print(f"   OURA_REFRESH_TOKEN={token.refresh_token}")
    print()

    await oauth.close()


if __name__ == "__main__":
    asyncio.run(main())
