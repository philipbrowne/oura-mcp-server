"""Token storage for OAuth2 authentication."""

import json
import os
import time
from pathlib import Path

from .models import OAuth2Token


class EnvTokenStore:
    """Environment variable-based token storage for cloud deployments.

    Reads tokens from OURA_ACCESS_TOKEN and OURA_REFRESH_TOKEN
    environment variables. Does not support writing (tokens must be set via
    environment configuration).
    """

    def load_token(self) -> OAuth2Token | None:
        """Load token from environment variables."""
        access_token = os.environ.get("OURA_ACCESS_TOKEN")

        if not access_token:
            return None

        return OAuth2Token(
            access_token=access_token,
            refresh_token=os.environ.get("OURA_REFRESH_TOKEN"),
        )

    def save_token(self, token: OAuth2Token) -> None:
        """Not supported - tokens must be set via environment variables."""
        raise NotImplementedError(
            "EnvTokenStore does not support saving tokens. "
            "Set OURA_ACCESS_TOKEN and OURA_REFRESH_TOKEN env vars."
        )

    def delete_token(self) -> None:
        """Not supported - tokens must be removed via environment variables."""
        pass

    def has_token(self) -> bool:
        """Check if access token env var is set."""
        return bool(os.environ.get("OURA_ACCESS_TOKEN"))


class TokenStore:
    """File-based token persistence for OAuth2 tokens.

    Stores tokens in a JSON file at the configured path with secure permissions.
    """

    def __init__(self, storage_path: str) -> None:
        """Initialize the token store.

        Args:
            storage_path: Path to the token storage file (supports ~ expansion).
        """
        self._storage_path = Path(os.path.expanduser(storage_path))
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the storage directory exists with secure permissions."""
        directory = self._storage_path.parent
        if not directory.exists():
            directory.mkdir(parents=True, mode=0o700)

    def _read_storage(self) -> dict:
        """Read the storage file.

        Returns:
            Dictionary containing stored data, or empty dict if file doesn't exist.
        """
        if not self._storage_path.exists():
            return {}
        try:
            with open(self._storage_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_storage(self, data: dict) -> None:
        """Write data to the storage file with secure permissions.

        Args:
            data: Dictionary to write to storage.
        """
        self._ensure_directory()

        # Write to temp file first, then rename for atomicity
        temp_path = self._storage_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)

        # Set secure permissions (owner read/write only)
        os.chmod(temp_path, 0o600)

        # Atomic rename
        temp_path.rename(self._storage_path)

    def save_token(self, token: OAuth2Token) -> None:
        """Save an OAuth2 token.

        Args:
            token: The token to save.
        """
        data = self._read_storage()
        data["token"] = {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "token_type": token.token_type,
            "expires_in": token.expires_in,
            "created_at": token.created_at or time.time(),
        }
        self._write_storage(data)

    def load_token(self) -> OAuth2Token | None:
        """Load the stored OAuth2 token.

        Returns:
            The token if it exists, None otherwise.
        """
        data = self._read_storage()
        token_data = data.get("token")
        if not token_data:
            return None
        return OAuth2Token(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in"),
            created_at=token_data.get("created_at"),
        )

    def delete_token(self) -> None:
        """Delete the stored token."""
        data = self._read_storage()
        if "token" in data:
            del data["token"]
            self._write_storage(data)

    def has_token(self) -> bool:
        """Check if a token is stored.

        Returns:
            True if a token exists, False otherwise.
        """
        return self.load_token() is not None
