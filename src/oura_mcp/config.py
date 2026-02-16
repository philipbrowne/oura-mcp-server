"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Oura MCP Server settings."""

    model_config = SettingsConfigDict(
        env_prefix="OURA_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # OAuth2 credentials
    client_id: str
    client_secret: str

    # API base URL
    api_base_url: str = "https://api.ouraring.com"

    # OAuth2 endpoints
    oauth_authorize_url: str = "https://cloud.ouraring.com/oauth/authorize"
    oauth_token_url: str = "https://api.ouraring.com/oauth/token"
    oauth_revoke_url: str = "https://api.ouraring.com/oauth/revoke"

    # OAuth2 scopes
    oauth_scopes: str = "email personal daily heartrate workout tag session spo2 stress ring_configuration heart_health"

    # Token storage path
    token_storage_path: str = "~/.config/oura-mcp/tokens.json"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
