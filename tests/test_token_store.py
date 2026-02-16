"""Tests for token storage."""

import os
import tempfile
from pathlib import Path

import pytest

from oura_mcp.models import OAuth2Token
from oura_mcp.token_store import TokenStore


@pytest.fixture
def temp_storage_path():
    """Create a temporary storage path for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "tokens.json")


@pytest.fixture
def token_store(temp_storage_path):
    """Create a TokenStore instance with temporary storage."""
    return TokenStore(temp_storage_path)


class TestTokenStore:
    """Tests for TokenStore class."""

    def test_save_and_load_token(self, token_store):
        """Test saving and loading a token."""
        token = OAuth2Token(
            access_token="test_access",
            refresh_token="test_refresh",
            expires_in=86400,
            created_at=1234567890.0,
        )

        token_store.save_token(token)
        loaded = token_store.load_token()

        assert loaded is not None
        assert loaded.access_token == "test_access"
        assert loaded.refresh_token == "test_refresh"
        assert loaded.expires_in == 86400
        assert loaded.created_at == 1234567890.0

    def test_load_token_not_exists(self, token_store):
        """Test loading a token when none exists."""
        loaded = token_store.load_token()
        assert loaded is None

    def test_delete_token(self, token_store):
        """Test deleting a token."""
        token = OAuth2Token(
            access_token="test_access",
            refresh_token="test_refresh",
        )

        token_store.save_token(token)
        assert token_store.load_token() is not None

        token_store.delete_token()
        assert token_store.load_token() is None

    def test_delete_token_not_exists(self, token_store):
        """Test deleting a token when none exists (no error)."""
        token_store.delete_token()  # Should not raise

    def test_has_token_true(self, token_store):
        """Test has_token when token exists."""
        token = OAuth2Token(
            access_token="test_access",
            refresh_token="test_refresh",
        )
        token_store.save_token(token)

        assert token_store.has_token() is True

    def test_has_token_false(self, token_store):
        """Test has_token when no token exists."""
        assert token_store.has_token() is False

    def test_storage_file_permissions(self, temp_storage_path, token_store):
        """Test that storage file has secure permissions."""
        token = OAuth2Token(
            access_token="test_access",
            refresh_token="test_refresh",
        )
        token_store.save_token(token)

        # Check file permissions (should be 0600)
        stat = os.stat(temp_storage_path)
        mode = stat.st_mode & 0o777
        assert mode == 0o600

    def test_storage_directory_permissions(self, temp_storage_path, token_store):
        """Test that storage directory has secure permissions."""
        nested_path = os.path.join(
            os.path.dirname(temp_storage_path), "nested", "dir", "tokens.json"
        )
        store = TokenStore(nested_path)

        token = OAuth2Token(
            access_token="test_access",
            refresh_token="test_refresh",
        )
        store.save_token(token)

        # Check directory permissions (should be 0700)
        parent_dir = Path(nested_path).parent
        stat = os.stat(parent_dir)
        mode = stat.st_mode & 0o777
        assert mode == 0o700

    def test_token_created_at_auto_set(self, token_store):
        """Test that created_at is auto-set when not provided."""
        token = OAuth2Token(
            access_token="test_access",
            refresh_token="test_refresh",
        )

        token_store.save_token(token)
        loaded = token_store.load_token()

        assert loaded is not None
        assert loaded.created_at is not None
        assert loaded.created_at > 0

    def test_handles_corrupted_storage(self, temp_storage_path, token_store):
        """Test that corrupted storage is handled gracefully."""
        # Write invalid JSON
        with open(temp_storage_path, "w") as f:
            f.write("not valid json")

        # Should return None, not raise
        loaded = token_store.load_token()
        assert loaded is None

    def test_tilde_expansion(self):
        """Test that ~ is expanded in storage path."""
        store = TokenStore("~/.config/test-oura/tokens.json")

        assert "~" not in str(store._storage_path)
        assert store._storage_path.is_absolute()

    def test_overwrite_existing_token(self, token_store):
        """Test that saving overwrites existing token."""
        token1 = OAuth2Token(
            access_token="first_token",
            refresh_token="first_refresh",
        )
        token2 = OAuth2Token(
            access_token="second_token",
            refresh_token="second_refresh",
        )

        token_store.save_token(token1)
        token_store.save_token(token2)

        loaded = token_store.load_token()
        assert loaded is not None
        assert loaded.access_token == "second_token"
        assert loaded.refresh_token == "second_refresh"

    def test_token_without_refresh(self, token_store):
        """Test saving and loading a token without refresh token."""
        token = OAuth2Token(
            access_token="access_only",
        )

        token_store.save_token(token)
        loaded = token_store.load_token()

        assert loaded is not None
        assert loaded.access_token == "access_only"
        assert loaded.refresh_token is None
