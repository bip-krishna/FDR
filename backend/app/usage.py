from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import ProviderUsage
from .settings import Settings


def current_month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _count_since(session: Session, since: datetime) -> int:
    return session.scalar(select(func.count()).select_from(ProviderUsage).where(
        ProviderUsage.provider == "serpapi", ProviderUsage.requested_at >= since,
    )) or 0


def provider_readiness(settings: Settings, session: Session | None = None) -> dict:
    if not settings.serpapi_enabled:
        reason = "provider_disabled"
    elif not settings.serpapi_key:
        reason = "missing_credentials"
    elif not settings.max_external_calls_day or not settings.max_external_calls_month:
        reason = "global_request_limits_not_configured"
    elif not settings.max_flight_searches_per_user_search:
        reason = "per_search_request_limit_not_configured"
    elif not settings.serpapi_monthly_search_limit or not settings.serpapi_daily_search_limit:
        reason = "provider_request_limits_not_configured"
    elif settings.serpapi_cost_per_search_inr is None:
        reason = "provider_cost_estimate_not_configured"
    else:
        reason = None
    limits = {
        "provider_monthly_search_limit": settings.serpapi_monthly_search_limit,
        "provider_daily_search_limit": settings.serpapi_daily_search_limit,
        "global_monthly_call_limit": settings.max_external_calls_month,
        "global_daily_call_limit": settings.max_external_calls_day,
        "calls_per_user_search_limit": settings.max_flight_searches_per_user_search,
    }
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if session is not None:
        month_used = _count_since(session, current_month_start(now))
        day_used = _count_since(session, now.replace(hour=0, minute=0, second=0, microsecond=0))
        spent = session.scalar(select(func.coalesce(func.sum(ProviderUsage.estimated_cost_inr), 0)).where(
            ProviderUsage.provider == "serpapi", ProviderUsage.requested_at >= current_month_start(now),
        )) or 0
    else:
        month_used = day_used = 0
        spent = 0
    if reason is None and session is not None:
        if month_used >= min(settings.max_external_calls_month, settings.serpapi_monthly_search_limit):
            reason = "monthly_request_limit_reached"
        elif day_used >= min(settings.max_external_calls_day, settings.serpapi_daily_search_limit):
            reason = "daily_request_limit_reached"
        elif float(spent) + (settings.serpapi_cost_per_search_inr or 0) > settings.monthly_external_budget_inr:
            reason = "monthly_spend_limit_reached"
    configuration_blockers = {
        "provider_disabled", "missing_credentials", "global_request_limits_not_configured",
        "per_search_request_limit_not_configured", "provider_request_limits_not_configured",
        "provider_cost_estimate_not_configured",
    }
    status = "unavailable" if reason in configuration_blockers else "blocked" if reason else "ready"
    return {"status": status, "reason": reason, "limits": limits,
            "month_calls_used": month_used, "day_calls_used": day_used}


def reserve_search_call(session: Session, settings: Settings, fingerprint: str,
                        calls_used_in_search: int) -> tuple[bool, str | None, ProviderUsage | None]:
    readiness = provider_readiness(settings)
    if readiness["status"] != "ready":
        return False, readiness["reason"], None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    month_start = current_month_start(now)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_total = _count_since(session, month_start)
    day_total = _count_since(session, day_start)
    serp_month = session.scalar(select(func.count()).select_from(ProviderUsage).where(
        ProviderUsage.provider == "serpapi", ProviderUsage.requested_at >= month_start,
    )) or 0
    serp_day = session.scalar(select(func.count()).select_from(ProviderUsage).where(
        ProviderUsage.provider == "serpapi", ProviderUsage.requested_at >= day_start,
    )) or 0
    spent = session.scalar(select(func.coalesce(func.sum(ProviderUsage.estimated_cost_inr), 0)).where(
        ProviderUsage.provider == "serpapi", ProviderUsage.requested_at >= month_start,
    )) or 0
    if calls_used_in_search >= settings.max_flight_searches_per_user_search:
        return False, "per_search_request_limit_reached", None
    if month_total >= settings.max_external_calls_month or serp_month >= settings.serpapi_monthly_search_limit:
        return False, "monthly_request_limit_reached", None
    if day_total >= settings.max_external_calls_day or serp_day >= settings.serpapi_daily_search_limit:
        return False, "daily_request_limit_reached", None
    estimate = settings.serpapi_cost_per_search_inr
    if estimate is None:
        return False, "provider_cost_estimate_not_configured", None
    if float(spent) + estimate > settings.monthly_external_budget_inr:
        return False, "monthly_spend_limit_reached", None

    usage = ProviderUsage(
        provider="serpapi", operation="google_flights_search", request_fingerprint=fingerprint,
        status="reserved", estimated_cost_inr=estimate, requested_at=now,
    )
    session.add(usage)
    session.commit()
    session.refresh(usage)
    return True, None, usage


def finish_search_call(session: Session, usage: ProviderUsage, status: str) -> None:
    usage.status = status
    usage.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(usage)
    session.commit()

