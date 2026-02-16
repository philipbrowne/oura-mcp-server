"""Custom exceptions for Oura MCP Server."""


class OuraError(Exception):
    """Base exception for Oura errors."""

    pass


class AuthenticationError(OuraError):
    """Raised when authentication fails."""

    pass


class TokenExpiredError(AuthenticationError):
    """Raised when the access token has expired."""

    pass


class TokenRefreshError(AuthenticationError):
    """Raised when token refresh fails."""

    pass


class APIError(OuraError):
    """Raised when the Oura API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    pass


class DataNotFoundError(APIError):
    """Raised when requested data is not found."""

    pass


class ConfigurationError(OuraError):
    """Raised when configuration is invalid or missing."""

    pass


class OAuthFlowError(OuraError):
    """Raised when OAuth handshake fails."""

    pass


class UserNotAuthenticatedError(OuraError):
    """Raised when an operation requires user auth but no user is connected."""

    pass
