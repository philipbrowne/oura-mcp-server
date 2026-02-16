"""OAuth2 Authorization Code flow for Oura Ring API."""

import time
import urllib.parse

import httpx

from .config import Settings
from .exceptions import OAuthFlowError
from .models import OAuth2Token
from .token_store import TokenStore


class OAuthFlowManager:
    """Manages the OAuth2 Authorization Code flow.

    This implements the two-step OAuth2 handshake:
    1. Generate an authorization URL for the user to visit
    2. Exchange the authorization code for an access token
    """

    def __init__(self, settings: Settings, token_store: TokenStore) -> None:
        """Initialize the OAuth flow manager.

        Args:
            settings: Application settings with OAuth endpoints.
            token_store: Token storage for persisting tokens.
        """
        self._settings = settings
        self._token_store = token_store
        self._client = httpx.AsyncClient()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def get_authorization_url(self) -> str:
        """Step 1: Generate the authorization URL for the user.

        Returns:
            URL for the user to visit to authorize the application.
        """
        params = {
            "response_type": "code",
            "client_id": self._settings.client_id,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "scope": self._settings.oauth_scopes,
        }
        return f"{self._settings.oauth_authorize_url}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> OAuth2Token:
        """Step 2: Exchange the authorization code for an access token.

        Args:
            code: The authorization code from the OAuth callback.

        Returns:
            OAuth2 token with access and refresh tokens.

        Raises:
            OAuthFlowError: If the exchange fails.
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "client_id": self._settings.client_id,
            "client_secret": self._settings.client_secret,
        }

        try:
            response = await self._client.post(
                self._settings.oauth_token_url,
                data=data,
            )
            response.raise_for_status()

            token_data = response.json()

            access_token = token_data.get("access_token")
            if not access_token:
                raise OAuthFlowError(
                    f"Invalid response from token endpoint: {token_data}"
                )

            token = OAuth2Token(
                access_token=access_token,
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                created_at=time.time(),
            )

            # Save the token
            self._token_store.save_token(token)

            return token

        except httpx.HTTPStatusError as e:
            raise OAuthFlowError(
                f"Failed to exchange code for token: HTTP {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise OAuthFlowError(f"Failed to exchange code for token: {str(e)}") from e

    async def revoke_token(self, token: str) -> None:
        """Revoke an access or refresh token (best-effort).

        Args:
            token: The token to revoke.
        """
        try:
            await self._client.post(
                self._settings.oauth_revoke_url,
                data={"token": token},
            )
        except Exception:
            pass  # Best-effort revocation
