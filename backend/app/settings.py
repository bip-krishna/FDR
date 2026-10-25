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
    )
