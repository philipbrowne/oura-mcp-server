"""Oura Ring MCP Server implementation using FastMCP."""

import os
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from .api_client import OuraClient
from .config import Settings, get_settings
from .exceptions import (
    APIError,
    ConfigurationError,
    OAuthFlowError,
    RateLimitError,
    TokenExpiredError,
    UserNotAuthenticatedError,
)
from .oauth_flow import OAuthFlowManager
from .token_store import EnvTokenStore, TokenStore

# Module-level holders for lifespan management
_client: OuraClient | None = None
_token_store: TokenStore | EnvTokenStore | None = None
_oauth_flow: OAuthFlowManager | None = None
_settings: Settings | None = None


@asynccontextmanager
async def lifespan(app: Any):
    """Lifespan context manager for the MCP server."""
    global _client, _token_store, _oauth_flow, _settings

    try:
        _settings = get_settings()
    except Exception as e:
        raise ConfigurationError(
            f"Failed to load settings. Ensure OURA_CLIENT_ID and "
            f"OURA_CLIENT_SECRET environment variables are set: {e}"
        ) from e

    # Initialize token store - use env vars on cloud deployments
    is_cloud = os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER")
    if is_cloud:
        _token_store = EnvTokenStore()
        _oauth_flow = None
    else:
        _token_store = TokenStore(_settings.token_storage_path)
        _oauth_flow = OAuthFlowManager(_settings, _token_store)

    # Load existing token if available
    token = _token_store.load_token()

    def _on_token_refresh(new_token):
        """Callback to persist refreshed tokens."""
        if _token_store and hasattr(_token_store, "save_token"):
            try:
                _token_store.save_token(new_token)
            except NotImplementedError:
                pass  # EnvTokenStore can't save

    _client = OuraClient(_settings, token=token, on_token_refresh=_on_token_refresh)

    try:
        yield
    finally:
        if _client:
            await _client.close()
            _client = None
        if _oauth_flow:
            await _oauth_flow.close()
            _oauth_flow = None
        _token_store = None
        _settings = None


# Create FastMCP server with lifespan
_mcp_host = os.environ.get("FASTMCP_HOST", "127.0.0.1")
_mcp_port = int(os.environ.get("PORT", os.environ.get("FASTMCP_PORT", "8000")))

mcp = FastMCP("oura", lifespan=lifespan, host=_mcp_host, port=_mcp_port)


def _get_client() -> OuraClient:
    """Get the OuraClient from module state."""
    if _client is None:
        raise RuntimeError("OuraClient not initialized - server not running")
    return _client


def _get_token_store() -> TokenStore | EnvTokenStore:
    """Get the TokenStore from module state."""
    if _token_store is None:
        raise RuntimeError("TokenStore not initialized - server not running")
    return _token_store


def _get_oauth_flow() -> OAuthFlowManager:
    """Get the OAuthFlowManager from module state."""
    if _oauth_flow is None:
        is_cloud = os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER")
        if is_cloud:
            raise RuntimeError(
                "OAuth flow not available on cloud deployment. "
                "Complete OAuth locally and set OURA_ACCESS_TOKEN and "
                "OURA_REFRESH_TOKEN environment variables."
            )
        raise RuntimeError("OAuthFlowManager not initialized - server not running")
    return _oauth_flow


def _get_settings() -> Settings:
    """Get the Settings from module state."""
    if _settings is None:
        raise RuntimeError("Settings not initialized - server not running")
    return _settings


async def _reinitialize_client() -> None:
    """Reinitialize the client with current token."""
    global _client

    settings = _get_settings()
    token_store = _get_token_store()

    if _client:
        await _client.close()

    token = token_store.load_token()

    def _on_token_refresh(new_token):
        if token_store:
            try:
                token_store.save_token(new_token)
            except NotImplementedError:
                pass

    _client = OuraClient(settings, token=token, on_token_refresh=_on_token_refresh)


def _format_duration(seconds: int | None) -> str:
    """Format seconds into a human-readable duration string."""
    if seconds is None:
        return "N/A"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


# ============================================================================
# Data Tools
# ============================================================================


@mcp.tool()
async def get_sleep_summary(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get daily sleep scores and contributors.

    Retrieve sleep score summaries for a date range. Shows overall sleep score
    and individual contributor scores (deep sleep, efficiency, latency, etc.).

    Args:
        start_date: Start date in YYYY-MM-DD format (defaults to last 7 days)
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        Formatted sleep summary with scores and contributors
    """
    try:
        client = _get_client()
        data = await client.get_daily_sleep(start_date, end_date)

        if not data:
            return "No sleep data found for the specified date range."

        output = [f"Sleep Summary ({len(data)} days):\n"]

        for day in data:
            output.append(f"  {day.day}: Score {day.score or 'N/A'}")
            if day.contributors:
                c = day.contributors
                parts = []
                if c.deep_sleep is not None:
                    parts.append(f"Deep: {c.deep_sleep}")
                if c.efficiency is not None:
                    parts.append(f"Efficiency: {c.efficiency}")
                if c.latency is not None:
                    parts.append(f"Latency: {c.latency}")
                if c.rem_sleep is not None:
                    parts.append(f"REM: {c.rem_sleep}")
                if c.restfulness is not None:
                    parts.append(f"Restfulness: {c.restfulness}")
                if c.timing is not None:
                    parts.append(f"Timing: {c.timing}")
                if c.total_sleep is not None:
                    parts.append(f"Total: {c.total_sleep}")
                if parts:
                    output.append(f"    Contributors: {' | '.join(parts)}")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting sleep data: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_activity_summary(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get daily activity summaries with steps, calories, and scores.

    Retrieve activity data including steps, calories burned, active time,
    and activity score with contributors.

    Args:
        start_date: Start date in YYYY-MM-DD format (defaults to last 7 days)
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        Formatted activity summary
    """
    try:
        client = _get_client()
        data = await client.get_daily_activity(start_date, end_date)

        if not data:
            return "No activity data found for the specified date range."

        output = [f"Activity Summary ({len(data)} days):\n"]

        for day in data:
            output.append(f"  {day.day}: Score {day.score or 'N/A'}")
            info = []
            if day.steps is not None:
                info.append(f"Steps: {day.steps:,}")
            if day.active_calories is not None:
                info.append(f"Active cal: {day.active_calories}")
            if day.total_calories is not None:
                info.append(f"Total cal: {day.total_calories}")
            if info:
                output.append(f"    {' | '.join(info)}")

            times = []
            if day.high_activity_time is not None:
                times.append(f"High: {_format_duration(day.high_activity_time)}")
            if day.medium_activity_time is not None:
                times.append(f"Medium: {_format_duration(day.medium_activity_time)}")
            if day.low_activity_time is not None:
                times.append(f"Low: {_format_duration(day.low_activity_time)}")
            if times:
                output.append(f"    Activity time: {' | '.join(times)}")

            if day.contributors:
                c = day.contributors
                parts = []
                if c.meet_daily_targets is not None:
                    parts.append(f"Targets: {c.meet_daily_targets}")
                if c.move_every_hour is not None:
                    parts.append(f"Hourly move: {c.move_every_hour}")
                if c.stay_active is not None:
                    parts.append(f"Stay active: {c.stay_active}")
                if c.training_frequency is not None:
                    parts.append(f"Training freq: {c.training_frequency}")
                if parts:
                    output.append(f"    Contributors: {' | '.join(parts)}")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting activity data: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_readiness_summary(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get daily readiness scores and contributors.

    Retrieve readiness data showing how ready your body is for the day,
    including contributor scores like HRV balance, resting heart rate, etc.

    Args:
        start_date: Start date in YYYY-MM-DD format (defaults to last 7 days)
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        Formatted readiness summary with scores and contributors
    """
    try:
        client = _get_client()
        data = await client.get_daily_readiness(start_date, end_date)

        if not data:
            return "No readiness data found for the specified date range."

        output = [f"Readiness Summary ({len(data)} days):\n"]

        for day in data:
            output.append(f"  {day.day}: Score {day.score or 'N/A'}")

            temps = []
            if day.temperature_deviation is not None:
                temps.append(f"Temp deviation: {day.temperature_deviation:+.1f}°C")
            if day.temperature_trend_deviation is not None:
                temps.append(f"Trend: {day.temperature_trend_deviation:+.1f}°C")
            if temps:
                output.append(f"    {' | '.join(temps)}")

            if day.contributors:
                c = day.contributors
                parts = []
                if c.activity_balance is not None:
                    parts.append(f"Activity balance: {c.activity_balance}")
                if c.body_temperature is not None:
                    parts.append(f"Body temp: {c.body_temperature}")
                if c.hrv_balance is not None:
                    parts.append(f"HRV: {c.hrv_balance}")
                if c.resting_heart_rate is not None:
                    parts.append(f"Resting HR: {c.resting_heart_rate}")
                if c.sleep_balance is not None:
                    parts.append(f"Sleep balance: {c.sleep_balance}")
                if c.previous_night is not None:
                    parts.append(f"Prev night: {c.previous_night}")
                if c.recovery_index is not None:
                    parts.append(f"Recovery: {c.recovery_index}")
                if parts:
                    output.append(f"    Contributors: {' | '.join(parts)}")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting readiness data: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_stress_data(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get daily stress and recovery data.

    Retrieve stress levels showing time in high stress vs recovery states,
    plus a daily summary classification.

    Args:
        start_date: Start date in YYYY-MM-DD format (defaults to last 7 days)
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        Formatted stress data with stress/recovery times
    """
    try:
        client = _get_client()
        data = await client.get_daily_stress(start_date, end_date)

        if not data:
            return "No stress data found for the specified date range."

        output = [f"Stress Data ({len(data)} days):\n"]

        for day in data:
            summary = day.day_summary or "N/A"
            output.append(f"  {day.day}: {summary}")
            info = []
            if day.stress_high is not None:
                info.append(f"High stress: {_format_duration(day.stress_high)}")
            if day.recovery_high is not None:
                info.append(f"Recovery: {_format_duration(day.recovery_high)}")
            if info:
                output.append(f"    {' | '.join(info)}")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting stress data: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_spo2_data(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get daily blood oxygen (SpO2) levels.

    Retrieve nightly blood oxygen saturation data and breathing
    disturbance index.

    Args:
        start_date: Start date in YYYY-MM-DD format (defaults to last 7 days)
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        Formatted SpO2 data
    """
    try:
        client = _get_client()
        data = await client.get_daily_spo2(start_date, end_date)

        if not data:
            return "No SpO2 data found for the specified date range."

        output = [f"SpO2 Data ({len(data)} days):\n"]

        for day in data:
            output.append(f"  {day.day}:")
            if day.spo2_percentage:
                avg = day.spo2_percentage.get("average")
                if avg is not None:
                    output.append(f"    Average SpO2: {avg}%")
            if day.breathing_disturbance_index is not None:
                output.append(
                    f"    Breathing disturbance index: "
                    f"{day.breathing_disturbance_index:.1f}"
                )

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting SpO2 data: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_sleep_details(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get detailed sleep period data including HRV, phases, and heart rate.

    Retrieve comprehensive sleep data for each sleep period including
    duration breakdowns, heart rate, HRV, breathing rate, and sleep phases.

    Args:
        start_date: Start date in YYYY-MM-DD format (defaults to last 7 days)
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        Detailed sleep period information
    """
    try:
        client = _get_client()
        data = await client.get_sleep_periods(start_date, end_date)

        if not data:
            return "No sleep period data found for the specified date range."

        output = [f"Sleep Periods ({len(data)} periods):\n"]

        for period in data:
            sleep_type = f" ({period.type})" if period.type else ""
            output.append(f"  {period.day}{sleep_type}:")

            if period.bedtime_start and period.bedtime_end:
                bs = period.bedtime_start
                be = period.bedtime_end
                start = bs.split("T")[1][:5] if "T" in bs else bs
                end = be.split("T")[1][:5] if "T" in be else be
                output.append(f"    Bedtime: {start} - {end}")

            durations = []
            if period.total_sleep_duration is not None:
                dur = _format_duration(period.total_sleep_duration)
                durations.append(f"Total sleep: {dur}")
            if period.deep_sleep_duration is not None:
                dur = _format_duration(period.deep_sleep_duration)
                durations.append(f"Deep: {dur}")
            if period.rem_sleep_duration is not None:
                dur = _format_duration(period.rem_sleep_duration)
                durations.append(f"REM: {dur}")
            if period.light_sleep_duration is not None:
                dur = _format_duration(period.light_sleep_duration)
                durations.append(f"Light: {dur}")
            if period.awake_time is not None:
                durations.append(f"Awake: {_format_duration(period.awake_time)}")
            if durations:
                output.append(f"    {' | '.join(durations)}")

            vitals = []
            if period.average_heart_rate is not None:
                vitals.append(f"Avg HR: {period.average_heart_rate} bpm")
            if period.lowest_heart_rate is not None:
                vitals.append(f"Lowest HR: {period.lowest_heart_rate} bpm")
            if period.average_hrv is not None:
                vitals.append(f"Avg HRV: {period.average_hrv} ms")
            if period.average_breath is not None:
                vitals.append(f"Breath: {period.average_breath:.1f}/min")
            if vitals:
                output.append(f"    {' | '.join(vitals)}")

            metrics = []
            if period.efficiency is not None:
                metrics.append(f"Efficiency: {period.efficiency}%")
            if period.latency is not None:
                metrics.append(f"Latency: {_format_duration(period.latency)}")
            if period.restless_periods is not None:
                metrics.append(f"Restless: {period.restless_periods}")
            if metrics:
                output.append(f"    {' | '.join(metrics)}")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting sleep details: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_heart_rate(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get heart rate samples with source context.

    Retrieve heart rate measurements throughout the day. Note: this can
    return many samples. Use narrow date ranges for best results.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Heart rate samples with timestamps and sources
    """
    try:
        client = _get_client()

        # Heart rate uses datetime params
        start_dt = f"{start_date}T00:00:00" if start_date else None
        end_dt = f"{end_date}T23:59:59" if end_date else None

        data = await client.get_heart_rate(start_dt, end_dt)

        if not data:
            return "No heart rate data found for the specified date range."

        # Summarize rather than dumping all samples
        output = [f"Heart Rate Data ({len(data)} samples):\n"]

        if data:
            bpms = [s.bpm for s in data if s.bpm is not None]
            if bpms:
                output.append(f"  Min: {min(bpms)} bpm")
                output.append(f"  Max: {max(bpms)} bpm")
                output.append(f"  Average: {sum(bpms) / len(bpms):.0f} bpm")

            # Show first and last timestamps
            first = data[0]
            last = data[-1]
            if first.timestamp:
                output.append(f"  First reading: {first.timestamp}")
            if last.timestamp:
                output.append(f"  Last reading: {last.timestamp}")

            # Group by source
            sources: dict[str, int] = {}
            for s in data:
                src = s.source or "unknown"
                sources[src] = sources.get(src, 0) + 1
            if sources:
                source_parts = [f"{k}: {v}" for k, v in sources.items()]
                output.append(f"  Sources: {' | '.join(source_parts)}")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting heart rate data: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_workouts(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get workout data including type, duration, and calories.

    Retrieve recorded workouts with activity type, duration, calories burned,
    distance, and intensity level.

    Args:
        start_date: Start date in YYYY-MM-DD format (defaults to last 7 days)
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        Formatted workout data
    """
    try:
        client = _get_client()
        data = await client.get_workouts(start_date, end_date)

        if not data:
            return "No workouts found for the specified date range."

        output = [f"Workouts ({len(data)}):\n"]

        for workout in data:
            activity = workout.activity or "Unknown"
            label = f" - {workout.label}" if workout.label else ""
            output.append(f"  {workout.day}: {activity}{label}")

            info = []
            if workout.duration is not None:
                info.append(f"Duration: {_format_duration(int(workout.duration))}")
            if workout.calories is not None:
                info.append(f"Calories: {workout.calories:.0f}")
            if workout.distance is not None:
                info.append(f"Distance: {workout.distance:.0f}m")
            if workout.intensity is not None:
                info.append(f"Intensity: {workout.intensity}")
            if info:
                output.append(f"    {' | '.join(info)}")

            if workout.source:
                output.append(f"    Source: {workout.source}")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting workouts: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_sessions(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get meditation, rest, and breathing sessions.

    Retrieve recorded rest sessions including meditation, breathing exercises,
    and other mindfulness activities.

    Args:
        start_date: Start date in YYYY-MM-DD format (defaults to last 7 days)
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        Formatted session data
    """
    try:
        client = _get_client()
        data = await client.get_sessions(start_date, end_date)

        if not data:
            return "No sessions found for the specified date range."

        output = [f"Sessions ({len(data)}):\n"]

        for session in data:
            session_type = session.type or "Unknown"
            output.append(f"  {session.day}: {session_type}")

            info = []
            if session.duration is not None:
                info.append(f"Duration: {_format_duration(session.duration)}")
            if session.mood is not None:
                info.append(f"Mood: {session.mood}")
            if info:
                output.append(f"    {' | '.join(info)}")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting sessions: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_personal_info() -> str:
    """Get user profile information.

    Retrieve basic user profile data from Oura including age, weight,
    height, and biological sex.

    Returns:
        User profile information
    """
    try:
        client = _get_client()
        info = await client.get_personal_info()

        output = ["Personal Info:\n"]

        if info.email:
            output.append(f"  Email: {info.email}")
        if info.age is not None:
            output.append(f"  Age: {info.age}")
        if info.biological_sex:
            output.append(f"  Biological sex: {info.biological_sex}")
        if info.height is not None:
            output.append(f"  Height: {info.height} cm")
        if info.weight is not None:
            output.append(f"  Weight: {info.weight} kg")

        if len(output) == 1:
            output.append("  No profile data available.")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting personal info: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_daily_resilience(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get daily resilience level and contributors.

    Retrieve resilience data showing how well your body handles stress
    and recovers, including the resilience level classification.

    Args:
        start_date: Start date in YYYY-MM-DD format (defaults to last 7 days)
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        Formatted resilience data
    """
    try:
        client = _get_client()
        data = await client.get_daily_resilience(start_date, end_date)

        if not data:
            return "No resilience data found for the specified date range."

        output = [f"Resilience Data ({len(data)} days):\n"]

        for day in data:
            level = day.level or "N/A"
            output.append(f"  {day.day}: Level {level}")
            if day.contributors:
                parts = [
                    f"{k}: {v}" for k, v in day.contributors.items() if v is not None
                ]
                if parts:
                    output.append(f"    Contributors: {' | '.join(parts)}")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting resilience data: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_sleep_recommendations(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """Get optimal bedtime window and sleep recommendations.

    Retrieve personalized sleep timing recommendations including
    the optimal bedtime window.

    Args:
        start_date: Start date in YYYY-MM-DD format (defaults to last 7 days)
        end_date: End date in YYYY-MM-DD format (defaults to today)

    Returns:
        Sleep timing recommendations
    """
    try:
        client = _get_client()
        data = await client.get_sleep_time(start_date, end_date)

        if not data:
            return "No sleep recommendation data found for the specified date range."

        output = [f"Sleep Recommendations ({len(data)} days):\n"]

        for day in data:
            output.append(f"  {day.day}:")
            if day.recommendation:
                output.append(f"    Recommendation: {day.recommendation}")
            if day.status:
                output.append(f"    Status: {day.status}")
            if day.optimal_bedtime:
                end = day.optimal_bedtime.get("end_offset")
                start = day.optimal_bedtime.get("start_offset")
                if start is not None and end is not None:
                    output.append(f"    Optimal window: {start}s - {end}s offset")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to Oura.\n"
            "Use start_authentication to connect your account first."
        )
    except TokenExpiredError:
        return (
            "Error: Session expired. Please re-authenticate using start_authentication."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting sleep recommendations: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# Authentication Tools
# ============================================================================


@mcp.tool()
async def check_auth_status() -> str:
    """Check if an Oura Ring account is connected.

    Returns whether you have user authentication configured, which is
    required for accessing health data.

    Returns:
        Authentication status message
    """
    try:
        client = _get_client()

        if client.is_authenticated:
            return (
                "Connected: Your Oura Ring account is linked.\n"
                "You can access sleep, activity, readiness, and other health data."
            )
        else:
            return (
                "Not connected: No Oura Ring account is linked.\n"
                "Use start_authentication to connect your account and enable "
                "access to your health data."
            )
    except Exception as e:
        return f"Error checking auth status: {str(e)}"


@mcp.tool()
async def start_authentication() -> str:
    """Start the Oura Ring account connection process.

    Begins the OAuth2 authentication flow. Returns a URL that the user must
    visit to authorize the connection. After authorizing, the user will
    receive an authorization code to use with complete_authentication.

    Note: Not available on cloud deployments. Complete OAuth locally first.

    Returns:
        Instructions with the authorization URL
    """
    try:
        oauth_flow = _get_oauth_flow()

        auth_url = oauth_flow.get_authorization_url()

        return (
            "To connect your Oura Ring account:\n\n"
            f"1. Visit this URL:\n   {auth_url}\n\n"
            "2. Log in to Oura and authorize the connection\n\n"
            "3. Copy the authorization code shown\n\n"
            "4. Use complete_authentication with the code to finish setup"
        )

    except RuntimeError as e:
        return str(e)
    except OAuthFlowError as e:
        return f"Error starting authentication: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def complete_authentication(code: str) -> str:
    """Complete the Oura Ring account connection.

    Finish the OAuth2 authentication flow using the authorization code
    obtained from the authorization page.

    Args:
        code: The authorization code from Oura's authorization page

    Returns:
        Success or error message
    """
    try:
        oauth_flow = _get_oauth_flow()

        await oauth_flow.exchange_code_for_token(code)

        # Reinitialize client with new credentials
        await _reinitialize_client()

        return (
            "Success! Your Oura Ring account is now connected.\n"
            "You can now access sleep, activity, readiness, and other health data."
        )

    except OAuthFlowError as e:
        return f"Error completing authentication: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def disconnect_account() -> str:
    """Disconnect your Oura Ring account.

    Remove stored credentials and disconnect from your Oura Ring account.
    You will need to re-authenticate to access health data again.

    Returns:
        Confirmation message
    """
    try:
        token_store = _get_token_store()

        # Try to revoke the token first
        if _oauth_flow and _token_store:
            token = _token_store.load_token()
            if token:
                await _oauth_flow.revoke_token(token.access_token)

        # Delete stored tokens
        token_store.delete_token()

        # Reinitialize client without auth
        await _reinitialize_client()

        return (
            "Disconnected: Your Oura Ring account has been unlinked.\n"
            "Health data access is no longer available.\n"
            "Use start_authentication to connect again."
        )

    except Exception as e:
        return f"Error disconnecting account: {str(e)}"


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    """Run the Oura MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
