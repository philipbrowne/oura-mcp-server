"""Oura Ring API client implementation."""

import time
from typing import Any

import httpx

from .config import Settings
from .exceptions import (
    APIError,
    DataNotFoundError,
    RateLimitError,
    TokenExpiredError,
    TokenRefreshError,
    UserNotAuthenticatedError,
)
from .models import (
    DailyActivity,
    DailyReadiness,
    DailyResilience,
    DailySleep,
    DailySpO2,
    DailyStress,
    HeartRateSample,
    OAuth2Token,
    PersonalInfo,
    Session,
    SleepPeriod,
    SleepTime,
    Tag,
    Workout,
)


class OuraClient:
    """Client for interacting with the Oura Ring API v2.

    Handles Bearer token authentication, automatic token refresh on 401,
    and cursor-based pagination.
    """

    def __init__(
        self,
        settings: Settings,
        token: OAuth2Token | None = None,
        on_token_refresh: Any = None,
    ) -> None:
        """Initialize the Oura API client.

        Args:
            settings: Application settings containing API configuration.
            token: Optional OAuth2 token for authenticated requests.
            on_token_refresh: Callback to persist refreshed tokens.
        """
        self._settings = settings
        self._token = token
        self._on_token_refresh = on_token_refresh
        self._client = httpx.AsyncClient()

    @property
    def is_authenticated(self) -> bool:
        """Check if client has an access token."""
        return self._token is not None

    def _require_auth(self) -> None:
        """Raise an error if not authenticated."""
        if not self.is_authenticated:
            raise UserNotAuthenticatedError(
                "This operation requires authentication. "
                "Please connect your Oura account first."
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "OuraClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def _refresh_token(self) -> None:
        """Refresh the access token using the refresh token.

        Raises:
            TokenRefreshError: If refresh fails.
        """
        if not self._token or not self._token.refresh_token:
            raise TokenRefreshError("No refresh token available")

        try:
            response = await self._client.post(
                self._settings.oauth_token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._token.refresh_token,
                    "client_id": self._settings.client_id,
                    "client_secret": self._settings.client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()

            self._token = OAuth2Token(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", self._token.refresh_token),
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in"),
                created_at=time.time(),
            )

            # Notify callback to persist the new token
            if self._on_token_refresh:
                self._on_token_refresh(self._token)

        except httpx.HTTPStatusError as e:
            raise TokenRefreshError(
                f"Token refresh failed: HTTP {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise TokenRefreshError(f"Token refresh failed: {str(e)}") from e

    async def _make_request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request to the Oura API.

        Automatically retries once on 401 after refreshing the token.

        Args:
            endpoint: The API endpoint path (e.g., "/v2/usercollection/daily_sleep").
            params: Optional query parameters.

        Returns:
            The JSON response from the API.

        Raises:
            APIError: If the API returns an error.
            RateLimitError: If rate limit is exceeded.
            TokenExpiredError: If token is expired and refresh fails.
        """
        self._require_auth()

        url = f"{self._settings.api_base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self._token.access_token}"}

        try:
            response = await self._client.get(url, headers=headers, params=params)

            # Auto-refresh on 401
            if response.status_code == 401:
                try:
                    await self._refresh_token()
                except TokenRefreshError:
                    raise TokenExpiredError(
                        "Access token expired and refresh failed. "
                        "Please re-authenticate."
                    )

                # Retry with new token
                headers = {"Authorization": f"Bearer {self._token.access_token}"}
                response = await self._client.get(url, headers=headers, params=params)

            if response.status_code == 429:
                raise RateLimitError(
                    "Rate limit exceeded. Please try again later.",
                    status_code=429,
                )

            if response.status_code == 404:
                raise DataNotFoundError(
                    "Requested data not found.",
                    status_code=404,
                )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise APIError(
                f"HTTP error {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code,
            )
        except httpx.RequestError as e:
            raise APIError(f"Request error: {str(e)}")

    async def _get_paginated(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> list[dict]:
        """Fetch all pages of a paginated endpoint.

        Follows next_token cursor through all pages.

        Args:
            endpoint: The API endpoint path.
            params: Optional query parameters.

        Returns:
            Combined list of all data items across all pages.
        """
        all_data: list[dict] = []
        current_params = dict(params) if params else {}

        while True:
            response = await self._make_request(endpoint, current_params)
            data = response.get("data", [])
            all_data.extend(data)

            next_token = response.get("next_token")
            if not next_token:
                break

            current_params["next_token"] = next_token

        return all_data

    # ========================================================================
    # Personal Info
    # ========================================================================

    async def get_personal_info(self) -> PersonalInfo:
        """Get user personal information."""
        data = await self._make_request("/v2/usercollection/personal_info")
        return PersonalInfo(**data)

    # ========================================================================
    # Daily Summaries
    # ========================================================================

    async def get_daily_sleep(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[DailySleep]:
        """Get daily sleep summaries."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/daily_sleep", params)
        return [DailySleep(**item) for item in items]

    async def get_daily_activity(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[DailyActivity]:
        """Get daily activity summaries."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/daily_activity", params)
        return [DailyActivity(**item) for item in items]

    async def get_daily_readiness(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[DailyReadiness]:
        """Get daily readiness summaries."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/daily_readiness", params)
        return [DailyReadiness(**item) for item in items]

    async def get_daily_stress(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[DailyStress]:
        """Get daily stress data."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/daily_stress", params)
        return [DailyStress(**item) for item in items]

    async def get_daily_spo2(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[DailySpO2]:
        """Get daily SpO2 (blood oxygen) data."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/daily_spo2", params)
        return [DailySpO2(**item) for item in items]

    async def get_daily_resilience(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[DailyResilience]:
        """Get daily resilience data."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/daily_resilience", params)
        return [DailyResilience(**item) for item in items]

    # ========================================================================
    # Detailed Data
    # ========================================================================

    async def get_sleep_periods(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[SleepPeriod]:
        """Get detailed sleep periods."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/sleep", params)
        return [SleepPeriod(**item) for item in items]

    async def get_sleep_time(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[SleepTime]:
        """Get recommended sleep/bedtime data."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/sleep_time", params)
        return [SleepTime(**item) for item in items]

    async def get_heart_rate(
        self,
        start_datetime: str | None = None,
        end_datetime: str | None = None,
    ) -> list[HeartRateSample]:
        """Get heart rate samples."""
        params: dict[str, Any] = {}
        if start_datetime:
            params["start_datetime"] = start_datetime
        if end_datetime:
            params["end_datetime"] = end_datetime

        items = await self._get_paginated("/v2/usercollection/heartrate", params)
        return [HeartRateSample(**item) for item in items]

    async def get_workouts(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[Workout]:
        """Get workouts."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/workout", params)
        return [Workout(**item) for item in items]

    async def get_sessions(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[Session]:
        """Get rest/meditation/breathing sessions."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/session", params)
        return [Session(**item) for item in items]

    async def get_tags(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[Tag]:
        """Get user tags."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        items = await self._get_paginated("/v2/usercollection/tag", params)
        return [Tag(**item) for item in items]
