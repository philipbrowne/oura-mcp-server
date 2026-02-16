"""Pytest fixtures for Oura MCP Server tests."""

import pytest

from oura_mcp.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Return a Settings object with test credentials."""
    return Settings(
        client_id="test_client_id",
        client_secret="test_client_secret",
        api_base_url="https://api.ouraring.com",
    )


@pytest.fixture
def mock_daily_sleep_response() -> dict:
    """Return a mock daily sleep API response."""
    return {
        "data": [
            {
                "id": "sleep_1",
                "day": "2024-01-15",
                "score": 85,
                "timestamp": "2024-01-15T00:00:00+00:00",
                "contributors": {
                    "deep_sleep": 80,
                    "efficiency": 90,
                    "latency": 75,
                    "rem_sleep": 85,
                    "restfulness": 70,
                    "timing": 88,
                    "total_sleep": 82,
                },
            },
            {
                "id": "sleep_2",
                "day": "2024-01-16",
                "score": 72,
                "timestamp": "2024-01-16T00:00:00+00:00",
                "contributors": {
                    "deep_sleep": 65,
                    "efficiency": 78,
                    "latency": 60,
                    "rem_sleep": 70,
                    "restfulness": 55,
                    "timing": 80,
                    "total_sleep": 68,
                },
            },
        ],
        "next_token": None,
    }


@pytest.fixture
def mock_daily_activity_response() -> dict:
    """Return a mock daily activity API response."""
    return {
        "data": [
            {
                "id": "activity_1",
                "day": "2024-01-15",
                "score": 90,
                "timestamp": "2024-01-15T04:00:00+00:00",
                "active_calories": 450,
                "total_calories": 2200,
                "steps": 8500,
                "equivalent_walking_distance": 6800,
                "high_activity_time": 1800,
                "medium_activity_time": 3600,
                "low_activity_time": 7200,
                "sedentary_time": 28800,
                "contributors": {
                    "meet_daily_targets": 85,
                    "move_every_hour": 70,
                    "recovery_time": 90,
                    "stay_active": 80,
                    "training_frequency": 75,
                    "training_volume": 88,
                },
            },
        ],
        "next_token": None,
    }


@pytest.fixture
def mock_daily_readiness_response() -> dict:
    """Return a mock daily readiness API response."""
    return {
        "data": [
            {
                "id": "readiness_1",
                "day": "2024-01-15",
                "score": 78,
                "timestamp": "2024-01-15T00:00:00+00:00",
                "temperature_deviation": 0.2,
                "temperature_trend_deviation": -0.1,
                "contributors": {
                    "activity_balance": 80,
                    "body_temperature": 75,
                    "hrv_balance": 82,
                    "previous_day_activity": 70,
                    "previous_night": 85,
                    "recovery_index": 78,
                    "resting_heart_rate": 72,
                    "sleep_balance": 80,
                },
            },
        ],
        "next_token": None,
    }


@pytest.fixture
def mock_sleep_periods_response() -> dict:
    """Return a mock sleep periods API response."""
    return {
        "data": [
            {
                "id": "period_1",
                "day": "2024-01-15",
                "bedtime_start": "2024-01-14T23:15:00+00:00",
                "bedtime_end": "2024-01-15T07:30:00+00:00",
                "duration": 29700,
                "total_sleep_duration": 27000,
                "awake_time": 2700,
                "light_sleep_duration": 14400,
                "rem_sleep_duration": 7200,
                "deep_sleep_duration": 5400,
                "restless_periods": 12,
                "type": "long_sleep",
                "average_breath": 15.2,
                "average_heart_rate": 58.0,
                "average_hrv": 42,
                "lowest_heart_rate": 48,
                "latency": 600,
                "efficiency": 91,
            },
        ],
        "next_token": None,
    }


@pytest.fixture
def mock_heart_rate_response() -> dict:
    """Return a mock heart rate API response."""
    return {
        "data": [
            {
                "bpm": 62,
                "source": "awake",
                "timestamp": "2024-01-15T10:00:00+00:00",
            },
            {
                "bpm": 75,
                "source": "awake",
                "timestamp": "2024-01-15T10:05:00+00:00",
            },
            {
                "bpm": 55,
                "source": "rest",
                "timestamp": "2024-01-15T03:00:00+00:00",
            },
        ],
        "next_token": None,
    }


@pytest.fixture
def mock_workouts_response() -> dict:
    """Return a mock workouts API response."""
    return {
        "data": [
            {
                "id": "workout_1",
                "day": "2024-01-15",
                "activity": "running",
                "calories": 350.0,
                "distance": 5200.0,
                "start_datetime": "2024-01-15T07:00:00+00:00",
                "end_datetime": "2024-01-15T07:35:00+00:00",
                "duration": 2100.0,
                "intensity": "moderate",
                "source": "manual",
            },
        ],
        "next_token": None,
    }


@pytest.fixture
def mock_personal_info_response() -> dict:
    """Return a mock personal info API response."""
    return {
        "id": "user_1",
        "age": 35,
        "weight": 75.5,
        "height": 180.0,
        "biological_sex": "male",
        "email": "test@example.com",
    }


@pytest.fixture
def mock_daily_stress_response() -> dict:
    """Return a mock daily stress API response."""
    return {
        "data": [
            {
                "id": "stress_1",
                "day": "2024-01-15",
                "stress_high": 3600,
                "recovery_high": 7200,
                "day_summary": "restored",
            },
        ],
        "next_token": None,
    }


@pytest.fixture
def mock_paginated_response() -> list[dict]:
    """Return mock responses for pagination testing (two pages)."""
    return [
        {
            "data": [
                {"id": "item_1", "day": "2024-01-15", "score": 85},
            ],
            "next_token": "page2_token",
        },
        {
            "data": [
                {"id": "item_2", "day": "2024-01-16", "score": 90},
            ],
            "next_token": None,
        },
    ]


@pytest.fixture
def mock_token_response() -> dict:
    """Return a mock OAuth2 token response."""
    return {
        "access_token": "new_access_token_123",
        "refresh_token": "new_refresh_token_456",
        "token_type": "Bearer",
        "expires_in": 86400,
    }
