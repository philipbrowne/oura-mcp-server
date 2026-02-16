"""Tests for Oura API client module."""

import asyncio

import pytest
import respx
from httpx import Response

from oura_mcp.api_client import OuraClient
from oura_mcp.exceptions import (
    APIError,
    DataNotFoundError,
    RateLimitError,
    TokenExpiredError,
    UserNotAuthenticatedError,
)
from oura_mcp.models import (
    DailyActivity,
    DailyReadiness,
    DailySleep,
    DailyStress,
    HeartRateSample,
    OAuth2Token,
    PersonalInfo,
    SleepPeriod,
    Workout,
)


@pytest.fixture
def token() -> OAuth2Token:
    """Return a test OAuth2 token."""
    return OAuth2Token(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_in=86400,
    )


@pytest.mark.asyncio
async def test_get_daily_sleep(settings, token, mock_daily_sleep_response):
    """Test get_daily_sleep returns list of DailySleep."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/daily_sleep").mock(
            return_value=Response(200, json=mock_daily_sleep_response)
        )

        client = OuraClient(settings, token=token)
        result = await client.get_daily_sleep("2024-01-15", "2024-01-16")

        assert len(result) == 2
        assert all(isinstance(d, DailySleep) for d in result)
        assert result[0].score == 85
        assert result[0].day == "2024-01-15"
        assert result[0].contributors.deep_sleep == 80


@pytest.mark.asyncio
async def test_get_daily_activity(settings, token, mock_daily_activity_response):
    """Test get_daily_activity returns list of DailyActivity."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/daily_activity").mock(
            return_value=Response(200, json=mock_daily_activity_response)
        )

        client = OuraClient(settings, token=token)
        result = await client.get_daily_activity("2024-01-15", "2024-01-15")

        assert len(result) == 1
        assert isinstance(result[0], DailyActivity)
        assert result[0].steps == 8500
        assert result[0].active_calories == 450
        assert result[0].contributors.meet_daily_targets == 85


@pytest.mark.asyncio
async def test_get_daily_readiness(settings, token, mock_daily_readiness_response):
    """Test get_daily_readiness returns list of DailyReadiness."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/daily_readiness").mock(
            return_value=Response(200, json=mock_daily_readiness_response)
        )

        client = OuraClient(settings, token=token)
        result = await client.get_daily_readiness("2024-01-15", "2024-01-15")

        assert len(result) == 1
        assert isinstance(result[0], DailyReadiness)
        assert result[0].score == 78
        assert result[0].temperature_deviation == 0.2


@pytest.mark.asyncio
async def test_get_sleep_periods(settings, token, mock_sleep_periods_response):
    """Test get_sleep_periods returns list of SleepPeriod."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/sleep").mock(
            return_value=Response(200, json=mock_sleep_periods_response)
        )

        client = OuraClient(settings, token=token)
        result = await client.get_sleep_periods("2024-01-15", "2024-01-15")

        assert len(result) == 1
        assert isinstance(result[0], SleepPeriod)
        assert result[0].average_heart_rate == 58.0
        assert result[0].average_hrv == 42
        assert result[0].deep_sleep_duration == 5400
        assert result[0].type == "long_sleep"


@pytest.mark.asyncio
async def test_get_heart_rate(settings, token, mock_heart_rate_response):
    """Test get_heart_rate returns list of HeartRateSample."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/heartrate").mock(
            return_value=Response(200, json=mock_heart_rate_response)
        )

        client = OuraClient(settings, token=token)
        result = await client.get_heart_rate(
            "2024-01-15T00:00:00", "2024-01-15T23:59:59"
        )

        assert len(result) == 3
        assert all(isinstance(s, HeartRateSample) for s in result)
        assert result[0].bpm == 62
        assert result[0].source == "awake"


@pytest.mark.asyncio
async def test_get_workouts(settings, token, mock_workouts_response):
    """Test get_workouts returns list of Workout."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/workout").mock(
            return_value=Response(200, json=mock_workouts_response)
        )

        client = OuraClient(settings, token=token)
        result = await client.get_workouts("2024-01-15", "2024-01-15")

        assert len(result) == 1
        assert isinstance(result[0], Workout)
        assert result[0].activity == "running"
        assert result[0].calories == 350.0
        assert result[0].distance == 5200.0


@pytest.mark.asyncio
async def test_get_personal_info(settings, token, mock_personal_info_response):
    """Test get_personal_info returns PersonalInfo."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/personal_info").mock(
            return_value=Response(200, json=mock_personal_info_response)
        )

        client = OuraClient(settings, token=token)
        result = await client.get_personal_info()

        assert isinstance(result, PersonalInfo)
        assert result.age == 35
        assert result.weight == 75.5
        assert result.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_daily_stress(settings, token, mock_daily_stress_response):
    """Test get_daily_stress returns list of DailyStress."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/daily_stress").mock(
            return_value=Response(200, json=mock_daily_stress_response)
        )

        client = OuraClient(settings, token=token)
        result = await client.get_daily_stress("2024-01-15", "2024-01-15")

        assert len(result) == 1
        assert isinstance(result[0], DailyStress)
        assert result[0].day_summary == "restored"
        assert result[0].stress_high == 3600


@pytest.mark.asyncio
async def test_pagination(settings, token, mock_paginated_response):
    """Test that _get_paginated follows next_token through all pages."""
    with respx.mock:
        route = respx.get("https://api.ouraring.com/v2/usercollection/daily_sleep")
        route.side_effect = [
            Response(200, json=mock_paginated_response[0]),
            Response(200, json=mock_paginated_response[1]),
        ]

        client = OuraClient(settings, token=token)
        result = await client.get_daily_sleep("2024-01-15", "2024-01-16")

        assert len(result) == 2
        assert result[0].day == "2024-01-15"
        assert result[1].day == "2024-01-16"
        assert route.call_count == 2


@pytest.mark.asyncio
async def test_401_triggers_token_refresh(
    settings, token, mock_daily_sleep_response, mock_token_response
):
    """Test that 401 response triggers token refresh and retry."""
    with respx.mock:
        # First call returns 401, second (after refresh) returns success
        data_route = respx.get("https://api.ouraring.com/v2/usercollection/daily_sleep")
        data_route.side_effect = [
            Response(401, json={"detail": "Unauthorized"}),
            Response(200, json=mock_daily_sleep_response),
        ]

        # Token refresh endpoint
        respx.post("https://api.ouraring.com/oauth/token").mock(
            return_value=Response(200, json=mock_token_response)
        )

        client = OuraClient(settings, token=token)
        result = await client.get_daily_sleep("2024-01-15", "2024-01-16")

        assert len(result) == 2
        assert data_route.call_count == 2


@pytest.mark.asyncio
async def test_401_with_failed_refresh_raises_token_expired(settings, token):
    """Test that 401 with failed refresh raises TokenExpiredError."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/daily_sleep").mock(
            return_value=Response(401, json={"detail": "Unauthorized"})
        )

        # Token refresh also fails
        respx.post("https://api.ouraring.com/oauth/token").mock(
            return_value=Response(401, text="Invalid refresh token")
        )

        client = OuraClient(settings, token=token)

        with pytest.raises(TokenExpiredError):
            await client.get_daily_sleep()


@pytest.mark.asyncio
async def test_429_raises_rate_limit_error(settings, token):
    """Test that 429 response raises RateLimitError."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/daily_sleep").mock(
            return_value=Response(429, text="Rate limit exceeded")
        )

        client = OuraClient(settings, token=token)

        with pytest.raises(RateLimitError):
            await client.get_daily_sleep()


@pytest.mark.asyncio
async def test_404_raises_data_not_found_error(settings, token):
    """Test that 404 response raises DataNotFoundError."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/personal_info").mock(
            return_value=Response(404, text="Not found")
        )

        client = OuraClient(settings, token=token)

        with pytest.raises(DataNotFoundError):
            await client.get_personal_info()


@pytest.mark.asyncio
async def test_500_raises_api_error(settings, token):
    """Test that 500 response raises APIError."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/daily_sleep").mock(
            return_value=Response(500, text="Internal Server Error")
        )

        client = OuraClient(settings, token=token)

        with pytest.raises(APIError):
            await client.get_daily_sleep()


@pytest.mark.asyncio
async def test_unauthenticated_raises_error(settings):
    """Test that requests without token raise UserNotAuthenticatedError."""
    client = OuraClient(settings)

    with pytest.raises(UserNotAuthenticatedError):
        await client.get_daily_sleep()


@pytest.mark.asyncio
async def test_bearer_token_in_headers(settings, token, mock_daily_sleep_response):
    """Test that Bearer token is included in request headers."""
    with respx.mock:
        route = respx.get(
            "https://api.ouraring.com/v2/usercollection/daily_sleep"
        ).mock(return_value=Response(200, json=mock_daily_sleep_response))

        client = OuraClient(settings, token=token)
        await client.get_daily_sleep()

        assert route.called
        request = route.calls[0].request
        assert request.headers["authorization"] == "Bearer test_access_token"


@pytest.mark.asyncio
async def test_concurrent_requests(
    settings, token, mock_daily_sleep_response, mock_daily_activity_response
):
    """Test that concurrent API requests work correctly."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/daily_sleep").mock(
            return_value=Response(200, json=mock_daily_sleep_response)
        )
        respx.get("https://api.ouraring.com/v2/usercollection/daily_activity").mock(
            return_value=Response(200, json=mock_daily_activity_response)
        )

        client = OuraClient(settings, token=token)

        results = await asyncio.gather(
            client.get_daily_sleep(),
            client.get_daily_activity(),
        )

        assert len(results) == 2
        assert all(isinstance(r, list) for r in results)


@pytest.mark.asyncio
async def test_empty_response(settings, token):
    """Test handling of empty data response."""
    with respx.mock:
        respx.get("https://api.ouraring.com/v2/usercollection/daily_sleep").mock(
            return_value=Response(200, json={"data": [], "next_token": None})
        )

        client = OuraClient(settings, token=token)
        result = await client.get_daily_sleep("2024-01-15", "2024-01-15")

        assert result == []


@pytest.mark.asyncio
async def test_on_token_refresh_callback(
    settings, token, mock_token_response, mock_daily_sleep_response
):
    """Test that on_token_refresh callback is called after refresh."""
    refreshed_tokens = []

    def on_refresh(new_token):
        refreshed_tokens.append(new_token)

    with respx.mock:
        data_route = respx.get("https://api.ouraring.com/v2/usercollection/daily_sleep")
        data_route.side_effect = [
            Response(401, json={"detail": "Unauthorized"}),
            Response(200, json=mock_daily_sleep_response),
        ]

        respx.post("https://api.ouraring.com/oauth/token").mock(
            return_value=Response(200, json=mock_token_response)
        )

        client = OuraClient(settings, token=token, on_token_refresh=on_refresh)
        await client.get_daily_sleep()

        assert len(refreshed_tokens) == 1
        assert refreshed_tokens[0].access_token == "new_access_token_123"
