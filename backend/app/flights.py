import hashlib
import math
import re
from datetime import date, datetime, timezone
from typing import Any, Literal, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import Airport
from .settings import Settings

SERPAPI_ENDPOINT = "https://serpapi.com/search"
PASSENGER_AIRPORT_TYPES = {"large_airport", "medium_airport", "small_airport"}
TRAVEL_CLASS_IDS = {"economy": 1, "premium-economy": 2, "business": 3, "first": 4}


class FlightSearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    origin: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    departure_date: date
    travel_class: Literal["economy", "premium-economy", "business", "first"] = "economy"
    currency: str = Field(default="INR", min_length=3, max_length=3)
    adults: int = Field(default=1, ge=1, le=9)
    include_nearby_airports: bool = False

    @field_validator("departure_date")
    @classmethod
    def require_future_date(cls, value: date) -> date:
        if value <= datetime.now(timezone.utc).date():
            raise ValueError("Flight searches require a future departure date.")
        return value

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        value = value.upper()
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError("Currency must be a three-letter code.")
        return value

    @model_validator(mode="after")
    def route_must_differ(self):
        if self.origin.casefold() == self.destination.casefold():
            raise ValueError("Origin and destination must be different.")
        return self


class FlightSegment(BaseModel):
    airline: str | None = None
    flight_number: str | None = None
    departure_airport: str | None = None
    departure_code: str | None = None
    departure_local_time: str | None = None
    departure_at_utc: datetime | None = None
    arrival_airport: str | None = None
    arrival_code: str | None = None
    arrival_local_time: str | None = None
    arrival_at_utc: datetime | None = None
    duration_minutes: int | None = None
    aircraft: str | None = None
    travel_class: str | None = None


class FlightOffer(BaseModel):
    id: str
    searched_origin: str
    searched_destination: str
    origin_airport: str | None
    origin_code: str | None
    destination_airport: str | None
    destination_code: str | None
    segments: list[FlightSegment]
    stops: int
    layovers: list[dict[str, Any]]
    total_duration_minutes: int | None
    price: float | None
    currency: str
    airlines: list[str]
    booking_url: str | None
    source: str = "SerpApi Google Flights"
    status: Literal["live", "cached"]
    retrieved_at: datetime
    provider_created_at: str | None = None
    fare_note: str = "Provider-returned fare; availability and final price may change before booking."


class FlightSearchResponse(BaseModel):
    status: Literal["live", "cached", "unavailable", "blocked", "error"]
    reason: str | None = None
    message: str
    results: list[FlightOffer] = Field(default_factory=list)
    airport_pairs_searched: list[dict[str, str]] = Field(default_factory=list)
    airport_pairs_failed: list[dict[str, str]] = Field(default_factory=list)
    airport_pairs_not_searched: list[dict[str, str]] = Field(default_factory=list)
    calls_used: int = 0
    calls_allowed: int = 0
    source: str = "SerpApi Google Flights"
    retrieved_at: datetime | None = None


def attach_utc_schedule_times(offers: list[FlightOffer], airport_timezones: Mapping[str, str]) -> None:
    """Add UTC instants only when the airport-local schedule time is unambiguous."""
    def to_utc(local_value: str | None, code: str | None) -> datetime | None:
        if not local_value or not code or code.upper() not in airport_timezones:
            return None
        try:
            parsed = datetime.fromisoformat(local_value.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc)
            zone = ZoneInfo(airport_timezones[code.upper()])
        except (ValueError, ZoneInfoNotFoundError):
            return None
        candidates = [parsed.replace(tzinfo=zone, fold=fold) for fold in (0, 1)]
        valid = [candidate for candidate in candidates
                 if candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == parsed]
        distinct = {candidate.astimezone(timezone.utc) for candidate in valid}
        if len(distinct) != 1:
            return None
        return next(iter(distinct))

    for offer in offers:
        for segment in offer.segments:
            segment.departure_at_utc = to_utc(segment.departure_local_time, segment.departure_code)
            segment.arrival_at_utc = to_utc(segment.arrival_local_time, segment.arrival_code)


def airport_candidates(session, query: str, max_candidates: int = 3) -> list[Airport]:
    value = query.strip()
    if re.fullmatch(r"[A-Za-z]{3}", value):
        exact = session.query(Airport).filter(Airport.iata_code == value.upper()).first()
        matches = [exact] if exact else []
    else:
        matches = session.query(Airport).filter(
            Airport.scheduled_service.is_(True), Airport.type.in_(PASSENGER_AIRPORT_TYPES),
            Airport.iata_code.is_not(None),
            (Airport.municipality.ilike(f"%{value}%") | Airport.name.ilike(f"{value}%")),
        ).limit(100).all()
    matches = [airport for airport in matches if airport and airport.scheduled_service is True
               and airport.type in PASSENGER_AIRPORT_TYPES and airport.iata_code]
    matches.sort(key=lambda a: (
        0 if a.iata_code and a.iata_code.casefold() == value.casefold() else 1,
        0 if a.municipality and a.municipality.casefold() == value.casefold() else 1,
        {"large_airport": 0, "medium_airport": 1, "small_airport": 2}.get(a.type, 3),
        (a.municipality or "").casefold(), a.name.casefold(),
    ))
    return matches[:max_candidates]


def expand_nearby_airports(session, city_matches: list[Airport], include_nearby: bool,
                           max_candidates: int = 3, radius_km: float = 250) -> list[Airport]:
    if not city_matches:
        return []
    if not include_nearby:
        return city_matches[:1]
    anchor = city_matches[0]
    if anchor.latitude_deg is None or anchor.longitude_deg is None:
        return city_matches[:max_candidates]

    candidates = session.query(Airport).filter(
        Airport.scheduled_service.is_(True), Airport.type.in_(PASSENGER_AIRPORT_TYPES),
        Airport.iata_code.is_not(None), Airport.latitude_deg.is_not(None), Airport.longitude_deg.is_not(None),
    ).all()
    ranked = []
    for airport in candidates:
        lat1, lon1 = math.radians(anchor.latitude_deg), math.radians(anchor.longitude_deg)
        lat2, lon2 = math.radians(airport.latitude_deg), math.radians(airport.longitude_deg)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        haversine = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        distance = 12742.0176 * math.asin(math.sqrt(min(1, haversine)))
        if distance <= radius_km:
            ranked.append((distance, {"large_airport": 0, "medium_airport": 1, "small_airport": 2}.get(airport.type, 3), airport.name.casefold(), airport))
    ranked.sort(key=lambda item: item[:3])
    if not ranked:
        return city_matches[:max_candidates]
    return [item[3] for item in ranked[:max_candidates]]


def airport_pair_shortlist(origins: list[Airport], destinations: list[Airport], include_nearby: bool,
                           max_calls: int) -> tuple[list[tuple[Airport, Airport]], list[tuple[Airport, Airport]]]:
    if not origins or not destinations or max_calls <= 0:
        return [], []
    candidates = origins if include_nearby else origins[:1]
    destinations = destinations if include_nearby else destinations[:1]
    ordered = [(origin, destination) for i, origin in enumerate(candidates)
               for j, destination in enumerate(destinations) if origin.id != destination.id]
    ordered.sort(key=lambda pair: (
        int(pair[0] is not origins[0]) + int(pair[1] is not destinations[0]),
        int(pair[0] is not origins[0]), int(pair[1] is not destinations[0]),
        pair[0].iata_code or "", pair[1].iata_code or "",
    ))
    return ordered[:max_calls], ordered[max_calls:]


def params_for_search(request: FlightSearchRequest, origin_code: str, destination_code: str,
                      settings: Settings) -> dict[str, str | int]:
    return {
        "engine": "google_flights", "departure_id": origin_code, "arrival_id": destination_code,
        "outbound_date": request.departure_date.isoformat(), "type": 2,
        "travel_class": TRAVEL_CLASS_IDS[request.travel_class], "currency": request.currency,
        "adults": request.adults,
        "gl": settings.default_google_country, "hl": settings.default_google_language,
        "no_cache": "false",
    }


def request_fingerprint(params: dict[str, Any]) -> str:
    normalized = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _metadata_is_cached(metadata: dict[str, Any], retrieved_at: datetime) -> bool:
    if metadata.get("cached") is True or str(metadata.get("status", "")).casefold() == "cached":
        return True
    created = metadata.get("created_at")
    if isinstance(created, str):
        try:
            created_at = datetime.strptime(created.removesuffix(" UTC"), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            return (retrieved_at - created_at).total_seconds() > 90
        except ValueError:
            pass
    return False


def normalize_response(payload: dict[str, Any], request: FlightSearchRequest, origin: Airport,
                       destination: Airport, retrieved_at: datetime) -> tuple[list[FlightOffer], bool]:
    metadata = payload.get("search_metadata") or {}
    provider_currency = (payload.get("search_parameters") or {}).get("currency")
    response_currency = provider_currency if isinstance(provider_currency, str) and re.fullmatch(
        r"[A-Z]{3}", provider_currency.upper()
    ) else request.currency
    result_status: Literal["live", "cached"] = "cached" if _metadata_is_cached(metadata, retrieved_at) else "live"
    booking_url = metadata.get("google_flights_url")
    if not isinstance(booking_url, str) or not booking_url.startswith("https://www.google.com/travel/flights"):
        booking_url = None
    offers = []
    for result in (payload.get("best_flights") or []) + (payload.get("other_flights") or []):
        flights = result.get("flights") or []
        if not flights:
            continue
        segments = []
        airlines = []
        for flight in flights:
            dep = flight.get("departure_airport") or {}
            arr = flight.get("arrival_airport") or {}
            airline = flight.get("airline")
            if airline and airline not in airlines:
                airlines.append(airline)
            segments.append(FlightSegment(
                airline=airline, flight_number=flight.get("flight_number"),
                departure_airport=dep.get("name"), departure_code=dep.get("id"),
                departure_local_time=dep.get("time"), arrival_airport=arr.get("name"),
                arrival_code=arr.get("id"), arrival_local_time=arr.get("time"),
                duration_minutes=flight.get("duration"), aircraft=flight.get("airplane"),
                travel_class=flight.get("travel_class"),
            ))
        identity = "|".join((str(origin.iata_code), str(destination.iata_code),
                             *(segment.flight_number or "" for segment in segments),
                             str(result.get("price")), str(request.departure_date)))
        offers.append(FlightOffer(
            id=hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20],
            searched_origin=request.origin, searched_destination=request.destination,
            origin_airport=(flights[0].get("departure_airport") or {}).get("name") or origin.name,
            origin_code=(flights[0].get("departure_airport") or {}).get("id") or origin.iata_code,
            destination_airport=(flights[-1].get("arrival_airport") or {}).get("name") or destination.name,
            destination_code=(flights[-1].get("arrival_airport") or {}).get("id") or destination.iata_code,
            segments=segments, stops=max(0, len(segments) - 1),
            layovers=result.get("layovers") if isinstance(result.get("layovers"), list) else [],
            total_duration_minutes=result.get("total_duration"),
            price=result.get("price") if isinstance(result.get("price"), (int, float)) else None,
            currency=response_currency.upper(), airlines=airlines, booking_url=booking_url,
            status=result_status, retrieved_at=retrieved_at,
            provider_created_at=metadata.get("created_at"),
        ))
    return offers, result_status == "cached"


async def search_serpapi(params: dict[str, Any], api_key: str, timeout: float,
                         transport: httpx.AsyncBaseTransport | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
        response = await client.get(SERPAPI_ENDPOINT, params={**params, "api_key": api_key})
        if response.status_code == 429:
            raise ProviderError("provider_rate_limited")
        if response.status_code in (401, 403):
            raise ProviderError("provider_authentication_failed")
        if response.status_code >= 500:
            raise ProviderError("provider_unavailable")
        if response.status_code >= 400:
            raise ProviderError("provider_request_rejected")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("invalid_provider_response") from exc
        if not isinstance(payload, dict):
            raise ProviderError("invalid_provider_response")
        if payload.get("error"):
            message = str(payload["error"]).casefold()
            if "rate" in message or "limit" in message or "quota" in message:
                raise ProviderError("provider_rate_limited")
            if "key" in message or "auth" in message:
                raise ProviderError("provider_authentication_failed")
            raise ProviderError("provider_request_rejected")
        return payload


class ProviderError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)
