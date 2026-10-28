"""Groq-backed ordering of trusted layover candidates, never a source of travel facts."""

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class VerifiedPlace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=180)
    source: str = Field(min_length=1, max_length=100)
    source_status: str
    opening_status: str
    traffic_status: str
    airport_to_place_minutes: int = Field(ge=0, le=720)
    place_to_airport_minutes: int = Field(ge=0, le=720)
    visit_minutes: int = Field(ge=1, le=720)
    opens_at: datetime
    closes_at: datetime
    known_cost_amount: float | None = Field(default=None, ge=0)
    known_cost_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


class LayoverPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    arrival_at: datetime
    departure_at: datetime
    exit_eligibility: Literal["verified_yes", "verified_no", "unknown"] = "unknown"
    baggage_recheck_required: bool = False
    disclaimer_acknowledged: bool = False
    interests: list[str] = Field(default_factory=list, max_length=8)
    # Until inter-attraction routes are backed by verified travel-time data,
    # keep any generated plan to one independently feasible place.
    max_places: int = Field(default=1, ge=1, le=1)

    @field_validator("interests")
    @classmethod
    def clean_interests(cls, values):
        cleaned = [" ".join(value.split())[:80] for value in values if value.strip()]
        return cleaned[:8]

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.arrival_at.tzinfo is None or self.departure_at.tzinfo is None:
            raise ValueError("Layover schedule times must include timezone offsets.")
        if self.departure_at <= self.arrival_at:
            raise ValueError("Onward departure must be after arrival.")
        return self


class ModelSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ordered_candidate_ids: list[str] = Field(max_length=5)


@dataclass(frozen=True)
class PlanConstraints:
    arrival_at: datetime
    departure_at: datetime
    exploration_start_at: datetime
    latest_return_at: datetime
    return_buffer_minutes: int = 180
    terminal_buffer_minutes: int = 60
    baggage_recheck_required: bool = False
    exit_eligibility_verified: bool = False


class InvalidItinerary(ValueError):
    pass


def validate_candidate(candidate: VerifiedPlace, constraints: PlanConstraints) -> None:
    if not constraints.exit_eligibility_verified:
        raise InvalidItinerary("Airport exit eligibility has not been independently verified.")
    if constraints.baggage_recheck_required:
        raise InvalidItinerary("Baggage re-check time is unknown; leaving the airport cannot be recommended.")
    if candidate.source_status not in {"live", "cached"}:
        raise InvalidItinerary("Candidate source is not verified live or cached data.")
    if candidate.opening_status != "verified" or candidate.traffic_status != "verified":
        raise InvalidItinerary("Candidate opening hours and traffic route must both be verified.")
    times = (candidate.opens_at, candidate.closes_at)
    if any(value.tzinfo is None for value in times):
        raise InvalidItinerary("Candidate opening hours must include timezone offsets.")
    if candidate.closes_at <= candidate.opens_at:
        raise InvalidItinerary("Candidate opening window is invalid.")
    if candidate.known_cost_amount is None and candidate.known_cost_currency is not None:
        raise InvalidItinerary("Candidate cost currency cannot be supplied without a known amount.")
    arrive_place = constraints.exploration_start_at + timedelta(minutes=candidate.airport_to_place_minutes)
    finish_visit = arrive_place + timedelta(minutes=candidate.visit_minutes)
    return_to_airport = finish_visit + timedelta(minutes=candidate.place_to_airport_minutes)
    if arrive_place < candidate.opens_at or finish_visit > candidate.closes_at:
        raise InvalidItinerary("Candidate is not open for the full planned visit.")
    if return_to_airport > constraints.latest_return_at:
        raise InvalidItinerary("Candidate visit and return route exceed the safe airport return deadline.")


def validate_model_selection(selection: ModelSelection, candidates: list[VerifiedPlace],
                             constraints: PlanConstraints, max_places: int) -> dict:
    candidate_map = {candidate.candidate_id: candidate for candidate in candidates}
    ordered_ids = selection.ordered_candidate_ids
    if len(ordered_ids) > max_places or len(set(ordered_ids)) != len(ordered_ids):
        raise InvalidItinerary("The model returned too many or repeated candidates.")
    if not ordered_ids:
        return {"status": "unavailable", "reason": "no_candidate_selected",
                "message": "No verified candidate matched the stated preferences."}
    if any(candidate_id not in candidate_map for candidate_id in ordered_ids):
        raise InvalidItinerary("The model selected a candidate that was not supplied.")
    result = []
    for candidate_id in ordered_ids:
        candidate = candidate_map[candidate_id]
        validate_candidate(candidate, constraints)
        arrive_place = constraints.exploration_start_at + timedelta(minutes=candidate.airport_to_place_minutes)
        finish_visit = arrive_place + timedelta(minutes=candidate.visit_minutes)
        return_airport = finish_visit + timedelta(minutes=candidate.place_to_airport_minutes)
        result.append({"candidate_id": candidate_id, "name": candidate.name,
            "source": candidate.source, "source_status": candidate.source_status,
            "arrive_place_at": arrive_place.isoformat(), "finish_visit_at": finish_visit.isoformat(),
            "return_to_airport_at": return_airport.isoformat(),
            "known_cost_amount": candidate.known_cost_amount,
            "known_cost_currency": candidate.known_cost_currency,
            "explanation": "Selected from the verified candidate list based on your stated preferences. This selection does not independently verify local conditions."})
    return {"status": "ready", "places": result,
        "warnings": ["Airport exit eligibility remains your responsibility; FDR does not authorize leaving the airport."],
        "latest_recommended_airport_return_at": constraints.latest_return_at.isoformat(),
        "airport_exit_authorized": False,
        "disclaimer": "Suggested layover activities are estimates and not guarantees. Traffic, immigration, airport security, flight schedules, and local conditions may change. Confirm that you are allowed to leave and re-enter the airport. Verify your boarding requirements and return early enough for your onward journey. The platform cannot guarantee that a connection will be made."}


SCHEMA = {
    "type": "object",
    "properties": {
        "ordered_candidate_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
    },
    "required": ["ordered_candidate_ids"],
    "additionalProperties": False,
}


async def request_groq_selection(*, api_key: str, model: str, timeout: float,
                                 interests: list[str], candidates: list[VerifiedPlace],
                                 constraints: PlanConstraints, max_places: int) -> ModelSelection:
    """Ask Groq to order verified candidates. It cannot supply any factual fields."""
    context = {
        "interests": interests,
        "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
        "constraints": {
            "exploration_start_at": constraints.exploration_start_at.isoformat(),
            "latest_return_at": constraints.latest_return_at.isoformat(),
            "max_places": max_places,
        },
    }
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": 900,
        "messages": [
            {"role": "system", "content": "Choose and order only supplied candidate IDs to match stated interests. Do not add places, hours, distances, traffic, procedures, visa claims, times, prices, explanations, warnings, or other facts. If none is a clear match, return an empty list. Return only the required JSON object."},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "layover_selection", "strict": True, "schema": SCHEMA}},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=body)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    try:
        return ModelSelection.model_validate_json(content)
    except (ValidationError, TypeError) as error:
        raise InvalidItinerary("Groq returned an invalid structured selection.") from error


async def plan_with_verified_candidates(*, request: LayoverPlanRequest,
                                        candidates: list[VerifiedPlace], settings, session,
                                        reserve_call, finish_call, selection_request=request_groq_selection) -> dict:
    """Validate context, reserve one capped request, call Groq, then validate again."""
    if not request.disclaimer_acknowledged:
        return {"status": "rejected", "reason": "disclaimer_not_acknowledged", "groq_called": False}
    if request.exit_eligibility != "verified_yes":
        return {"status": "rejected", "reason": "airport_exit_not_verified", "groq_called": False,
                "message": "FDR cannot treat unknown or unpermitted airport exit as safe."}
    if request.baggage_recheck_required:
        return {"status": "rejected", "reason": "baggage_recheck_time_unknown", "groq_called": False}
    if len(candidates) > 20:
        return {"status": "rejected", "reason": "candidate_limit_exceeded", "groq_called": False}
    if not candidates:
        return {"status": "unavailable", "reason": "verified_candidates_unavailable", "groq_called": False,
                "message": "No verified places with opening hours and traffic routes are available. No Groq request was made."}

    arrival = request.arrival_at.astimezone(timezone.utc)
    departure = request.departure_at.astimezone(timezone.utc)
    if departure <= arrival or (departure - arrival).total_seconds() < 10 * 3600:
        return {"status": "rejected", "reason": "layover_below_exploration_threshold", "groq_called": False}
    constraints = PlanConstraints(arrival_at=arrival, departure_at=departure,
        exploration_start_at=arrival + timedelta(minutes=60),
        latest_return_at=departure - timedelta(minutes=180),
        exit_eligibility_verified=True)
    ready_candidates = []
    rejected_candidates = []
    for candidate in candidates:
        try:
            validate_candidate(candidate, constraints)
            ready_candidates.append(candidate)
        except InvalidItinerary as error:
            rejected_candidates.append({"candidate_id": candidate.candidate_id, "reason": str(error)})
    if not ready_candidates:
        return {"status": "rejected", "reason": "no_feasible_verified_candidates", "groq_called": False,
                "rejected_candidates": rejected_candidates}
    if request.max_places != 1:
        return {"status": "rejected", "reason": "verified_inter_attraction_routes_unavailable", "groq_called": False}

    layover_identity = hashlib.sha256(
        f"{arrival.isoformat()}|{departure.isoformat()}".encode()).hexdigest()
    allowed, reason, usage = reserve_call(session, settings, layover_identity)
    if not allowed or usage is None:
        return {"status": "blocked" if reason and "limit" in reason else "unavailable",
                "reason": reason or "request_not_reserved", "groq_called": False}
    try:
        selection = await selection_request(api_key=settings.groq_api_key,
            model=settings.groq_layover_model, timeout=settings.request_timeout_seconds,
            interests=request.interests, candidates=ready_candidates,
            constraints=constraints, max_places=1)
        validated = validate_model_selection(selection, ready_candidates, constraints, max_places=1)
        finish_call(session, usage, "success")
        validated.update({"groq_called": True, "rejected_candidates": rejected_candidates,
                          "disclaimer_acknowledged": True})
        return validated
    except (httpx.HTTPError, InvalidItinerary, ValidationError, KeyError, IndexError, TypeError, ValueError) as error:
        finish_call(session, usage, "error")
        if isinstance(error, InvalidItinerary):
            return {"status": "rejected", "reason": "invalid_generated_itinerary", "message": str(error),
                    "groq_called": True}
        return {"status": "error", "reason": "groq_request_failed", "groq_called": True,
                "message": "Groq could not return a valid plan. No fallback itinerary was generated."}
