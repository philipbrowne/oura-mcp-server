"""Tests for OAuth2 Authorization Code flow."""

import os
import tempfile

import pytest
import respx
from httpx import Response

from oura_mcp.config import Settings
from oura_mcp.exceptions import OAuthFlowError
from oura_mcp.oauth_flow import OAuthFlowManager
from oura_mcp.token_store import TokenStore


@pytest.fixture
def settings():
    """Return settings for tests."""
    return Settings(
        client_id="test_client_id",
        client_secret="test_client_secret",
    )


@pytest.fixture
def temp_storage_path():
    """Create a temporary storage path for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "tokens.json")


@pytest.fixture
def token_store(temp_storage_path):
    """Create a TokenStore instance with temporary storage."""
    return TokenStore(temp_storage_path)


@pytest.fixture
def oauth_flow(settings, token_store):
    """Create an OAuthFlowManager instance."""
    return OAuthFlowManager(settings, token_store)


class TestOAuthFlowManager:
    """Tests for OAuthFlowManager class."""

    def test_get_authorization_url(self, oauth_flow):
        """Test authorization URL generation."""
        url = oauth_flow.get_authorization_url()

        assert "https://cloud.ouraring.com/oauth/authorize" in url
        assert "response_type=code" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=" in url
        assert "scope=" in url

    def test_get_authorization_url_contains_scopes(self, oauth_flow):
        """Test that authorization URL includes configured scopes."""
        url = oauth_flow.get_authorization_url()

        # Scopes should be URL-encoded in the query string
        assert "scope=" in url

    @respx.mock
    async def test_exchange_code_for_token_success(self, oauth_flow, token_store):
        """Test successful code exchange for token."""
        respx.post("https://api.ouraring.com/oauth/token").mock(
            return_value=Response(
                200,
                json={
                    "access_token": "access_token_123",
                    "refresh_token": "refresh_token_456",
                    "token_type": "Bearer",
                    "expires_in": 86400,
                },
            )
        )

        token = await oauth_flow.exchange_code_for_token("auth_code_789")

        assert token.access_token == "access_token_123"
        assert token.refresh_token == "refresh_token_456"
        assert token.token_type == "Bearer"
        assert token.expires_in == 86400
        assert token.created_at is not None

        # Verify token was saved to store
        saved = token_store.load_token()
        assert saved is not None
        assert saved.access_token == "access_token_123"

    @respx.mock
    async def test_exchange_code_http_error(self, oauth_flow):
        """Test code exchange with HTTP error."""
        respx.post("https://api.ouraring.com/oauth/token").mock(
            return_value=Response(401, text="Invalid code")
        )

        with pytest.raises(OAuthFlowError) as exc_info:
            await oauth_flow.exchange_code_for_token("invalid_code")

        assert "HTTP 401" in str(exc_info.value)

    @respx.mock
    async def test_exchange_code_invalid_response(self, oauth_flow):
        """Test code exchange with invalid response (missing access_token)."""
        respx.post("https://api.ouraring.com/oauth/token").mock(
            return_value=Response(200, json={"error": "invalid_grant"})
        )

        with pytest.raises(OAuthFlowError) as exc_info:
            await oauth_flow.exchange_code_for_token("bad_code")

        assert "Invalid response" in str(exc_info.value)

    @respx.mock
    async def test_revoke_token_success(self, oauth_flow):
        """Test successful token revocation."""
        route = respx.post("https://api.ouraring.com/oauth/revoke").mock(
            return_value=Response(200)
        )

        # Should not raise
        await oauth_flow.revoke_token("some_token")
        assert route.called

    @respx.mock
    async def test_revoke_token_failure_is_silent(self, oauth_flow):
        """Test that token revocation failure is silent (best-effort)."""
        respx.post("https://api.ouraring.com/oauth/revoke").mock(
            return_value=Response(500, text="Server Error")
        )

        # Should not raise even on error
        await oauth_flow.revoke_token("some_token")

    @respx.mock
    async def test_full_oauth_flow(self, oauth_flow, token_store):
        """Test the complete OAuth2 flow from URL generation to token exchange."""
        # Step 1: Generate authorization URL
        auth_url = oauth_flow.get_authorization_url()
        assert "client_id=test_client_id" in auth_url

        # Step 2: Exchange code for token
        respx.post("https://api.ouraring.com/oauth/token").mock(
            return_value=Response(
                200,
                json={
                    "access_token": "final_access",
                    "refresh_token": "final_refresh",
                    "token_type": "Bearer",
                    "expires_in": 86400,
                },
            )
        )

        token = await oauth_flow.exchange_code_for_token("user_auth_code")

        assert token.access_token == "final_access"
        assert token.refresh_token == "final_refresh"

        # Verify final state
        assert token_store.has_token() is True
        saved = token_store.load_token()
        assert saved.access_token == "final_access"

    async def test_close(self, oauth_flow):
        """Test closing the OAuth flow manager."""
        await oauth_flow.close()
        # Should not raise
