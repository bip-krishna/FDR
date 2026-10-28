"""Deterministic layover safety and attraction feasibility rules."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


DEFAULT_AIRPORT_RETURN_BUFFER_MINUTES = 180
DEFAULT_TERMINAL_BUFFER_MINUTES = 60
DEFAULT_MINIMUM_VISIT_MINUTES = 45


@dataclass(frozen=True)
class AttractionCandidate:
    place_id: str
    name: str
    one_way_travel_minutes: int | None
    visit_minutes: int = DEFAULT_MINIMUM_VISIT_MINUTES
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    source: str = "Google Places"
    source_status: str = "live"


def evaluate_layover(*, arrival_at: datetime, departure_at: datetime,
                     airport_return_buffer_minutes: int = DEFAULT_AIRPORT_RETURN_BUFFER_MINUTES,
                     terminal_transfer_buffer_minutes: int = DEFAULT_TERMINAL_BUFFER_MINUTES,
                     exit_eligibility: str = "unknown", baggage_recheck_required: bool = False,
                     candidates: list[AttractionCandidate] | None = None) -> dict:
    """Evaluate an airport layover in UTC; unknown exit eligibility never becomes approval."""
    if arrival_at.tzinfo is None or departure_at.tzinfo is None:
        raise ValueError("Layover schedule times must include a timezone offset.")
    arrival = arrival_at.astimezone(timezone.utc)
    departure = departure_at.astimezone(timezone.utc)
    if departure <= arrival:
        raise ValueError("Onward departure must be after arrival.")
    if not 0 <= airport_return_buffer_minutes <= 720 or not 0 <= terminal_transfer_buffer_minutes <= 360:
        raise ValueError("Safety buffers are outside the supported range.")

    total_minutes = int((departure - arrival).total_seconds() // 60)
    long_layover = total_minutes >= 600
    return_deadline = departure - timedelta(minutes=airport_return_buffer_minutes)
    exploration_start = arrival + timedelta(minutes=terminal_transfer_buffer_minutes)
    usable_minutes = max(0, int((return_deadline - exploration_start).total_seconds() // 60))
    eligibility = exit_eligibility if exit_eligibility in {"verified_yes", "verified_no", "unknown"} else "unknown"
    warnings = ["Immigration and airport-exit eligibility is unverified. FDR does not authorize leaving the airport."]
    if eligibility == "verified_no":
        warnings = ["Exit eligibility is marked not permitted. Do not leave the airport."]
    elif eligibility == "verified_yes":
        warnings = ["Exit eligibility was marked verified by the user; FDR has not independently confirmed it."]
    if baggage_recheck_required:
        warnings.append("Baggage re-check is required and its time is not included in the exploration window.")

    feasible = []
    rejected = []
    for place in candidates or []:
        reason = None
        travel = place.one_way_travel_minutes
        if eligibility != "verified_yes":
            reason = "airport_exit_not_verified"
        elif baggage_recheck_required:
            reason = "baggage_recheck_time_unknown"
        elif travel is None or travel < 0:
            reason = "round_trip_travel_time_unavailable"
        elif place.visit_minutes <= 0:
            reason = "invalid_visit_duration"
        elif (2 * travel + place.visit_minutes) > usable_minutes:
            reason = "insufficient_conservative_time"
        else:
            visit_start = exploration_start + timedelta(minutes=travel)
            visit_end = visit_start + timedelta(minutes=place.visit_minutes)
            if place.opens_at and visit_start < place.opens_at.astimezone(timezone.utc):
                reason = "place_not_open_at_arrival"
            elif place.closes_at and visit_end > place.closes_at.astimezone(timezone.utc):
                reason = "place_closes_before_visit_finishes"
        if reason:
            rejected.append({"place_id": place.place_id, "name": place.name, "reason": reason})
        else:
            feasible.append({"place_id": place.place_id, "name": place.name,
                "one_way_travel_minutes": travel, "visit_minutes": place.visit_minutes,
                "estimated_leave_airport_at": exploration_start.isoformat(),
                "estimated_arrive_place_at": visit_start.isoformat(),
                "estimated_finish_visit_at": visit_end.isoformat(),
                "source": place.source, "source_status": place.source_status,
                "opening_hours_status": "verified" if place.opens_at and place.closes_at else "unknown"})

    return {"status": "ready", "layover_minutes": total_minutes, "long_layover": long_layover,
        "exploration_eligible_by_duration": long_layover and usable_minutes > 0,
        "exit_eligibility": eligibility, "airport_exit_authorized": False,
        "exploration_start_at": exploration_start.isoformat(),
        "latest_recommended_airport_return_at": return_deadline.isoformat(),
        "available_exploration_minutes": usable_minutes,
        "airport_return_buffer_minutes": airport_return_buffer_minutes,
        "terminal_transfer_buffer_minutes": terminal_transfer_buffer_minutes,
        "weather_status": "unavailable", "route_traffic_status": "unavailable",
        "places_status": "unavailable", "warnings": warnings,
        "feasible_candidates": feasible, "rejected_candidates": rejected,
        "disclaimer": "Suggested layover activities are estimates and not guarantees. Traffic, immigration, airport security, flight schedules, and local conditions may change. Confirm that you are allowed to leave and re-enter the airport. Verify your boarding requirements and return early enough for your onward journey. The platform cannot guarantee that a connection will be made."}
