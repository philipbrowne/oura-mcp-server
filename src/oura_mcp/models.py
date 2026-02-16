"""Pydantic models for Oura API responses."""

from pydantic import BaseModel, Field

# ============================================================================
# Authentication Models
# ============================================================================


class OAuth2Token(BaseModel):
    """Model for OAuth2 token."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None
    created_at: float | None = None


# ============================================================================
# Personal Info
# ============================================================================


class PersonalInfo(BaseModel):
    """Model for user personal information."""

    id: str | None = None
    age: int | None = None
    weight: float | None = None
    height: float | None = None
    biological_sex: str | None = None
    email: str | None = None


# ============================================================================
# Sleep Models
# ============================================================================


class SleepContributors(BaseModel):
    """Contributors to sleep score."""

    deep_sleep: int | None = None
    efficiency: int | None = None
    latency: int | None = None
    rem_sleep: int | None = None
    restfulness: int | None = None
    timing: int | None = None
    total_sleep: int | None = None


class DailySleep(BaseModel):
    """Model for daily sleep summary."""

    id: str | None = None
    day: str | None = None
    score: int | None = None
    timestamp: str | None = None
    contributors: SleepContributors | None = None


class SleepPeriod(BaseModel):
    """Model for a detailed sleep period."""

    id: str | None = None
    day: str | None = None
    bedtime_start: str | None = None
    bedtime_end: str | None = None
    duration: int | None = None
    total_sleep_duration: int | None = None
    awake_time: int | None = None
    light_sleep_duration: int | None = None
    rem_sleep_duration: int | None = None
    deep_sleep_duration: int | None = None
    restless_periods: int | None = None
    sleep_phase_5_min: str | None = None
    type: str | None = None
    readiness_score_delta: float | None = None
    activity_score_delta: float | None = None
    average_breath: float | None = None
    average_heart_rate: float | None = None
    average_hrv: int | None = None
    lowest_heart_rate: int | None = None
    latency: int | None = None
    efficiency: int | None = None
    time_in_bed: int | None = None
    heart_rate: dict | None = None
    hrv: dict | None = None
    movement_30_sec: str | None = None
    sleep_algorithm_version: str | None = None


class SleepTime(BaseModel):
    """Model for recommended sleep time / bedtime window."""

    id: str | None = None
    day: str | None = None
    optimal_bedtime: dict | None = None
    recommendation: str | None = None
    status: str | None = None


# ============================================================================
# Activity Models
# ============================================================================


class ActivityContributors(BaseModel):
    """Contributors to activity score."""

    meet_daily_targets: int | None = None
    move_every_hour: int | None = None
    recovery_time: int | None = None
    stay_active: int | None = None
    training_frequency: int | None = None
    training_volume: int | None = None


class DailyActivity(BaseModel):
    """Model for daily activity summary."""

    id: str | None = None
    day: str | None = None
    score: int | None = None
    timestamp: str | None = None
    active_calories: int | None = None
    total_calories: int | None = None
    steps: int | None = None
    equivalent_walking_distance: int | None = None
    high_activity_time: int | None = None
    medium_activity_time: int | None = None
    low_activity_time: int | None = None
    sedentary_time: int | None = None
    resting_time: int | None = None
    non_wear_time: int | None = None
    high_activity_met_minutes: int | None = None
    medium_activity_met_minutes: int | None = None
    low_activity_met_minutes: int | None = None
    average_met_minutes: float | None = None
    target_calories: int | None = None
    target_meters: int | None = None
    met: dict | None = None
    contributors: ActivityContributors | None = None
    inactivity_alerts: int | None = None


# ============================================================================
# Readiness Models
# ============================================================================


class ReadinessContributors(BaseModel):
    """Contributors to readiness score."""

    activity_balance: int | None = None
    body_temperature: int | None = None
    hrv_balance: int | None = None
    previous_day_activity: int | None = None
    previous_night: int | None = None
    recovery_index: int | None = None
    resting_heart_rate: int | None = None
    sleep_balance: int | None = None


class DailyReadiness(BaseModel):
    """Model for daily readiness summary."""

    id: str | None = None
    day: str | None = None
    score: int | None = None
    timestamp: str | None = None
    temperature_deviation: float | None = None
    temperature_trend_deviation: float | None = None
    contributors: ReadinessContributors | None = None


# ============================================================================
# Stress Models
# ============================================================================


class DailyStress(BaseModel):
    """Model for daily stress data."""

    id: str | None = None
    day: str | None = None
    stress_high: int | None = None
    recovery_high: int | None = None
    day_summary: str | None = None


# ============================================================================
# SpO2 Models
# ============================================================================


class DailySpO2(BaseModel):
    """Model for daily blood oxygen data."""

    id: str | None = None
    day: str | None = None
    spo2_percentage: dict | None = None
    breathing_disturbance_index: float | None = None


# ============================================================================
# Resilience Models
# ============================================================================


class DailyResilience(BaseModel):
    """Model for daily resilience data."""

    id: str | None = None
    day: str | None = None
    level: str | None = None
    contributors: dict | None = None


# ============================================================================
# Heart Rate Models
# ============================================================================


class HeartRateSample(BaseModel):
    """Model for a heart rate sample."""

    bpm: int | None = None
    source: str | None = None
    timestamp: str | None = None


# ============================================================================
# Workout Models
# ============================================================================


class Workout(BaseModel):
    """Model for a workout."""

    id: str | None = None
    day: str | None = None
    activity: str | None = None
    calories: float | None = None
    distance: float | None = None
    start_datetime: str | None = None
    end_datetime: str | None = None
    duration: float | None = None
    intensity: str | None = None
    label: str | None = None
    source: str | None = None


# ============================================================================
# Session Models
# ============================================================================


class Session(BaseModel):
    """Model for a rest/meditation/breathing session."""

    id: str | None = None
    day: str | None = None
    type: str | None = None
    start_datetime: str | None = None
    end_datetime: str | None = None
    duration: int | None = None
    mood: str | None = None
    heart_rate: dict | None = None
    hrv: dict | None = None
    motion_count: dict | None = None


# ============================================================================
# Tag Models
# ============================================================================


class Tag(BaseModel):
    """Model for a user tag."""

    id: str | None = None
    day: str | None = None
    tag_type_code: str | None = None
    text: str | None = None
    timestamp: str | None = None
    start_day: str | None = None
    end_day: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    comment: str | None = None


# ============================================================================
# Ring Configuration
# ============================================================================


class RingConfiguration(BaseModel):
    """Model for ring configuration."""

    id: str | None = None
    color: str | None = None
    design: str | None = None
    firmware_version: str | None = None
    hardware_type: str | None = None
    set_up_at: str | None = None
    size: int | None = None


# ============================================================================
# Paginated Response
# ============================================================================


class PaginatedResponse(BaseModel):
    """Model for a paginated API response."""

    data: list[dict] = Field(default_factory=list)
    next_token: str | None = None
