import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _integer(name: str, default: int = 0) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _amount(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _enabled(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    serpapi_key: str | None
    serpapi_enabled: bool
    serpapi_monthly_search_limit: int
    serpapi_daily_search_limit: int
    max_external_calls_day: int
    max_external_calls_month: int
    max_flight_searches_per_user_search: int
    monthly_external_budget_inr: float
    serpapi_cost_per_search_inr: float | None
    request_timeout_seconds: float
    default_currency: str
    default_google_country: str
    default_google_language: str
    frontend_origins: tuple[str, ...]
    google_maps_key: str | None = None
    google_maps_enabled: bool = False
    google_geocoding_enabled: bool = False
    google_routes_enabled: bool = False
    google_geocoding_daily_limit: int = 0
    google_geocoding_monthly_limit: int = 0
    google_geocoding_cost_inr: float | None = None
    google_routes_daily_limit: int = 0
    google_routes_monthly_limit: int = 0
    google_routes_cost_inr: float | None = None
    max_google_maps_calls_per_transfer: int = 0
    google_maps_timeout_seconds: float = 20.0
    max_google_maps_calls_per_journey: int = 0
    airport_checkin_buffer_minutes: int = 120
    groq_api_key: str | None = None
    groq_layover_enabled: bool = False
    groq_layover_model: str = "openai/gpt-oss-20b"
    groq_daily_limit: int = 0
    groq_monthly_limit: int = 0
    groq_max_calls_per_layover: int = 0
    groq_cost_per_call_inr: float | None = None


def get_settings() -> Settings:
    try:
        timeout = max(1.0, min(60.0, float(os.getenv("SERPAPI_TIMEOUT_SECONDS", "20"))))
    except ValueError:
        timeout = 20.0
    try:
        budget = max(0.0, float(os.getenv("MONTHLY_EXTERNAL_API_BUDGET_INR", "0")))
    except ValueError:
        budget = 0.0
    key = os.getenv("SERPAPI_API_KEY", "").strip()
    try:
        maps_timeout = max(1.0, min(60.0, float(os.getenv("GOOGLE_MAPS_TIMEOUT_SECONDS", "20"))))
    except ValueError:
        maps_timeout = 20.0
    return Settings(
        serpapi_key=key or None,
        serpapi_enabled=_enabled("ENABLE_SERPAPI"),
        serpapi_monthly_search_limit=_integer("SERPAPI_MAX_CALLS_PER_MONTH"),
        serpapi_daily_search_limit=_integer("SERPAPI_MAX_CALLS_PER_DAY"),
        max_external_calls_day=_integer("MAX_EXTERNAL_API_CALLS_PER_DAY"),
        max_external_calls_month=_integer("MAX_EXTERNAL_API_CALLS_PER_MONTH"),
        max_flight_searches_per_user_search=_integer("MAX_FLIGHT_SEARCHES_PER_USER_SEARCH"),
        monthly_external_budget_inr=budget,
        serpapi_cost_per_search_inr=_amount("SERPAPI_COST_PER_SEARCH_INR"),
        request_timeout_seconds=timeout,
        default_currency=os.getenv("FLIGHT_DEFAULT_CURRENCY", "INR").strip().upper(),
        default_google_country=os.getenv("FLIGHT_GOOGLE_COUNTRY", "in").strip().lower(),
        default_google_language=os.getenv("FLIGHT_GOOGLE_LANGUAGE", "en").strip().lower(),
        frontend_origins=tuple(origin.strip() for origin in os.getenv(
            "FRONTEND_ORIGINS", "http://localhost:3000").split(",") if origin.strip()),
        google_maps_key=(os.getenv("GOOGLE_MAPS_API_KEY", "").strip() or None),
        google_maps_enabled=_enabled("ENABLE_GOOGLE_MAPS"),
        google_geocoding_enabled=_enabled("ENABLE_GOOGLE_GEOCODING"),
        google_routes_enabled=_enabled("ENABLE_GOOGLE_ROUTES"),
        google_geocoding_daily_limit=_integer("GOOGLE_GEOCODING_MAX_CALLS_PER_DAY"),
        google_geocoding_monthly_limit=_integer("GOOGLE_GEOCODING_MAX_CALLS_PER_MONTH"),
        google_geocoding_cost_inr=_amount("GOOGLE_GEOCODING_COST_PER_CALL_INR"),
        google_routes_daily_limit=_integer("GOOGLE_ROUTES_MAX_CALLS_PER_DAY"),
        google_routes_monthly_limit=_integer("GOOGLE_ROUTES_MAX_CALLS_PER_MONTH"),
        google_routes_cost_inr=_amount("GOOGLE_ROUTES_COST_PER_CALL_INR"),
        max_google_maps_calls_per_transfer=_integer("MAX_GOOGLE_MAPS_CALLS_PER_TRANSFER"),
        google_maps_timeout_seconds=maps_timeout,
        max_google_maps_calls_per_journey=_integer("MAX_GOOGLE_MAPS_CALLS_PER_JOURNEY"),
        airport_checkin_buffer_minutes=min(360, _integer("AIRPORT_CHECKIN_BUFFER_MINUTES", 120)),
        groq_api_key=(os.getenv("GROQ_API_KEY", "").strip() or None),
        groq_layover_enabled=_enabled("ENABLE_GROQ_LAYOVER"),
        groq_layover_model=os.getenv("GROQ_LAYOVER_MODEL", "openai/gpt-oss-20b").strip(),
        groq_daily_limit=_integer("GROQ_MAX_CALLS_PER_DAY"),
        groq_monthly_limit=_integer("GROQ_MAX_CALLS_PER_MONTH"),
        groq_max_calls_per_layover=_integer("MAX_GROQ_CALLS_PER_LAYOVER"),
        groq_cost_per_call_inr=_amount("GROQ_MAX_COST_PER_CALL_INR"),
    )
