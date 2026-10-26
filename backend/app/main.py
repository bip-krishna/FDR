import math
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .database import Base, engine
from .models import Airport
from .flights import (
    FlightSearchRequest, FlightSearchResponse, airport_candidates, airport_pair_shortlist, expand_nearby_airports,
    normalize_response, params_for_search, request_fingerprint, search_serpapi, ProviderError,
)
from .settings import get_settings
from .usage import finish_search_call, provider_readiness, reserve_search_call
from .usage import reserve_google_maps_call
from .google_maps import MapsProviderError, compute_route, fingerprint, geocode
from .journeys import calculate_door_to_door_timing
from .rail import (
    IRCTC_URL, NTES_URL, STATION_RETRIEVED_ON, STATION_SOURCE, STATION_SOURCE_URL,
    Station, find_stations,
)

SOURCE = "OurAirports"
DATASET_RETRIEVED_ON = date(2026, 10, 24)
ELIGIBLE_TYPES = {"large_airport", "medium_airport", "small_airport"}
EARTH_RADIUS_KM = 6371.0088

@asynccontextmanager
async def lifespan(_app):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="FDR Airport Discovery API", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().frontend_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class AirportRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    municipality: str | None
    iso_country: str | None
    type: str
    iata_code: str | None
    icao_code: str | None
    latitude_deg: float | None
    longitude_deg: float | None
    scheduled_service: bool | None
    passenger_service_eligible: bool
    source: str = SOURCE
    source_retrieved_on: date = DATASET_RETRIEVED_ON
    eligibility_note: str
    distance_km: float | None = None


class AirportResults(BaseModel):
    results: list[AirportRecord]
    source: str = SOURCE
    source_retrieved_on: date = DATASET_RETRIEVED_ON
    total: int


class TransferRequest(BaseModel):
    origin: str
    destination: str
    departure_time: datetime | None = None


class GroundAccessRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=160)
    destination: str = Field(min_length=2, max_length=160)
    departure_airport_code: str = Field(pattern=r"^[A-Za-z]{3}$")
    arrival_airport_code: str = Field(pattern=r"^[A-Za-z]{3}$")
    departure_local_time: str = Field(min_length=10, max_length=40)
    arrival_local_time: str = Field(min_length=10, max_length=40)
    flight_duration_minutes: int = Field(ge=1, le=2880)


def get_session():
    with SessionLocal() as session:
        yield session


def maps_unavailable_reason(settings, operation: str) -> str | None:
    if not settings.google_maps_enabled:
        return "google_maps_disabled"
    if not settings.google_maps_key:
        return "missing_credentials"
    if operation == "geocoding" and not settings.google_geocoding_enabled:
        return "google_geocoding_disabled"
    if operation == "routes" and not settings.google_routes_enabled:
        return "google_routes_disabled"
    if operation == "journey" and (not settings.google_geocoding_enabled or not settings.google_routes_enabled):
        return "google_maps_services_disabled"
    if not settings.max_external_calls_day or not settings.max_external_calls_month:
        return "global_request_limits_not_configured"
    request_limit = (settings.max_google_maps_calls_per_journey if operation == "journey"
                     else settings.max_google_maps_calls_per_transfer)
    if not request_limit:
        return "per_transfer_request_limit_not_configured"
    if operation == "geocoding" and (not settings.google_geocoding_daily_limit or
            not settings.google_geocoding_monthly_limit or settings.google_geocoding_cost_inr is None):
        return "geocoding_limits_or_cost_not_configured"
    if operation == "routes" and (not settings.google_routes_daily_limit or
            not settings.google_routes_monthly_limit or settings.google_routes_cost_inr is None):
        return "routes_limits_or_cost_not_configured"
    if operation == "journey" and (not settings.google_geocoding_daily_limit or
            not settings.google_geocoding_monthly_limit or settings.google_geocoding_cost_inr is None or
            not settings.google_routes_daily_limit or not settings.google_routes_monthly_limit or
            settings.google_routes_cost_inr is None):
        return "routes_or_geocoding_limits_or_cost_not_configured"
    return None


@app.get("/api/providers/google-maps")
def google_maps_status(session: Session = Depends(get_session)):
    settings = get_settings()
    reason = maps_unavailable_reason(settings, "geocoding") or maps_unavailable_reason(settings, "routes")
    return {"provider": "Google Maps Platform", "status": "unavailable" if reason else "configured",
            "reason": reason, "limits": {
                "geocoding_daily": settings.google_geocoding_daily_limit,
                "geocoding_monthly": settings.google_geocoding_monthly_limit,
                "routes_daily": settings.google_routes_daily_limit,
                "routes_monthly": settings.google_routes_monthly_limit,
                "calls_per_transfer": settings.max_google_maps_calls_per_transfer,
            }}


@app.post("/api/transfers/estimate")
async def estimate_transfer(request: TransferRequest, session: Session = Depends(get_session)):
    settings = get_settings()
    reason = maps_unavailable_reason(settings, "geocoding") or maps_unavailable_reason(settings, "routes")
    if reason:
        return {"status": "unavailable", "reason": reason,
                "message": "Ground transfer estimates are not configured. No Google Maps request was made."}
    origin_text, destination_text = request.origin.strip(), request.destination.strip()
    if not origin_text or not destination_text or len(origin_text) > 160 or len(destination_text) > 160:
        raise HTTPException(status_code=422, detail="Enter two locations of 1–160 characters.")
    departure = request.departure_time or datetime.now(timezone.utc)
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if departure < now.replace(second=0, microsecond=0):
        raise HTTPException(status_code=422, detail="Transfer departure time cannot be in the past.")
    call_count = 0
    fingerprint_base = fingerprint({"origin": origin_text.casefold(), "destination": destination_text.casefold()})
    locations = []
    for index, address in enumerate((origin_text, destination_text)):
        allowed, block, reservation = reserve_google_maps_call(session, settings, "geocoding",
            fingerprint(f"{fingerprint_base}:geocode:{index}"), call_count)
        if not allowed:
            return {"status": "blocked", "reason": block, "message": "Ground transfer stopped by its configured quota or cost limit.",
                    "calls_used": call_count}
        call_count += 1
        try:
            location = await geocode(address, settings.google_maps_key, settings.google_maps_timeout_seconds)
            finish_search_call(session, reservation, "success")
            locations.append(location)
        except (httpx.HTTPError, ValueError, KeyError, TypeError, MapsProviderError) as error:
            finish_search_call(session, reservation, getattr(error, "reason", "provider_error"))
            return {"status": "error", "reason": getattr(error, "reason", "provider_error"),
                    "message": "Google Maps could not resolve both locations; no route estimate is available.", "calls_used": call_count}

    allowed, block, reservation = reserve_google_maps_call(session, settings, "routes_traffic_aware",
        fingerprint(f"{fingerprint_base}:route"), call_count)
    if not allowed:
        return {"status": "blocked", "reason": block,
                "message": "Route estimate stopped by its configured quota or cost limit.", "calls_used": call_count}
    call_count += 1
    try:
        route = await compute_route(locations[0], locations[1], departure,
            settings.google_maps_key, settings.google_maps_timeout_seconds)
        finish_search_call(session, reservation, "success")
    except (httpx.HTTPError, ValueError, KeyError, TypeError, MapsProviderError) as error:
        finish_search_call(session, reservation, getattr(error, "reason", "provider_error"))
        return {"status": "error", "reason": getattr(error, "reason", "provider_error"),
                "message": "Google Maps could not calculate a drivable route at this time.", "calls_used": call_count}
    departure_mode = "current_traffic" if (departure - now).total_seconds() <= 900 else "future_prediction"
    arrival_time = datetime.fromtimestamp(departure.timestamp() + route["duration_seconds"], timezone.utc)
    return {"status": "ready", "origin": locations[0], "destination": locations[1], **route,
            "departure_time": departure.isoformat(), "traffic_mode": departure_mode,
            "arrival_time_estimate": arrival_time.isoformat(),
            "traffic_delay_seconds": max(0, route["duration_seconds"] - route["static_duration_seconds"]),
            "traffic_label": "Current traffic conditions" if departure_mode == "current_traffic" else "Future traffic prediction",
            "provider": "Google Maps Routes API", "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "calls_used": call_count, "ranking_duration_minutes": math.ceil(route["duration_seconds"] / 60)}


@app.post("/api/journeys/ground-access")
async def estimate_journey_ground_access(request: GroundAccessRequest, session: Session = Depends(get_session)):
    settings = get_settings()
    reason = maps_unavailable_reason(settings, "journey")
    if reason:
        return {"status": "unavailable", "reason": reason,
                "message": "Door-to-door access estimates are not configured. No Google Maps request was made."}
    limit = settings.max_google_maps_calls_per_journey
    if limit < 4:
        return {"status": "unavailable", "reason": "journey_call_limit_below_required",
                "message": "Each complete estimate needs two geocoding and two route requests. No provider call was made."}

    departure_airport = session.scalar(select(Airport).where(
        Airport.iata_code == request.departure_airport_code.upper(), Airport.scheduled_service.is_(True)))
    arrival_airport = session.scalar(select(Airport).where(
        Airport.iata_code == request.arrival_airport_code.upper(), Airport.scheduled_service.is_(True)))
    airports = [departure_airport, arrival_airport]
    if any(airport is None or airport.latitude_deg is None or airport.longitude_deg is None for airport in airports):
        return {"status": "unavailable", "reason": "airport_coordinates_unavailable",
                "message": "Airport coordinates are missing from the reference dataset. No Google Maps request was made."}
    try:
        from zoneinfo import ZoneInfo
        from timezonefinder import timezone_at

        departure_zone_name = timezone_at(lng=departure_airport.longitude_deg, lat=departure_airport.latitude_deg)
        arrival_zone_name = timezone_at(lng=arrival_airport.longitude_deg, lat=arrival_airport.latitude_deg)
        if not departure_zone_name or not arrival_zone_name:
            raise ValueError("Timezone could not be identified.")
        departure_local = datetime.fromisoformat(request.departure_local_time.replace("Z", "+00:00"))
        arrival_local = datetime.fromisoformat(request.arrival_local_time.replace("Z", "+00:00"))
        departure_at = departure_local.replace(tzinfo=ZoneInfo(departure_zone_name)) if departure_local.tzinfo is None else departure_local
        arrival_at = arrival_local.replace(tzinfo=ZoneInfo(arrival_zone_name)) if arrival_local.tzinfo is None else arrival_local
        departure_utc = departure_at.astimezone(timezone.utc)
        arrival_utc = arrival_at.astimezone(timezone.utc)
    except (ImportError, ValueError, TypeError, KeyError):
        return {"status": "unavailable", "reason": "airport_time_zone_unavailable",
                "message": "Airport time zones could not be resolved. No Google Maps request was made."}
    if departure_utc <= datetime.now(timezone.utc) or arrival_utc <= departure_utc:
        return {"status": "unavailable", "reason": "invalid_flight_timing",
                "message": "The provider flight times are incomplete or inconsistent. No Google Maps request was made."}
    scheduled_flight_minutes = math.ceil((arrival_utc - departure_utc).total_seconds() / 60)

    request_limit = settings.max_google_maps_calls_per_journey
    base_fingerprint = fingerprint({"origin": request.origin.casefold(), "destination": request.destination.casefold(),
        "departure_airport": request.departure_airport_code.upper(), "arrival_airport": request.arrival_airport_code.upper(),
        "departure": departure_utc.isoformat(), "arrival": arrival_utc.isoformat()})
    call_count = 0
    points = []
    for index, location_text in enumerate((request.origin, request.destination)):
        allowed, block, reservation = reserve_google_maps_call(session, settings, "geocoding",
            fingerprint(f"{base_fingerprint}:geocode:{index}"), call_count, request_limit)
        if not allowed:
            return {"status": "blocked", "reason": block, "calls_used": call_count,
                    "message": "Door-to-door calculation stopped at its configured quota or cost limit."}
        call_count += 1
        try:
            point = await geocode(location_text, settings.google_maps_key, settings.google_maps_timeout_seconds)
            finish_search_call(session, reservation, "success")
            points.append(point)
        except (httpx.HTTPError, ValueError, KeyError, TypeError, MapsProviderError) as error:
            finish_search_call(session, reservation, getattr(error, "reason", "provider_error"))
            return {"status": "error", "reason": getattr(error, "reason", "provider_error"), "calls_used": call_count,
                    "message": "A city location could not be resolved. No airport-access routes are available."}

    # Estimate the outbound drive at the configured check-in-buffer departure time.
    origin_drive_at = departure_utc - timedelta(minutes=settings.airport_checkin_buffer_minutes)
    if origin_drive_at < datetime.now(timezone.utc):
        origin_drive_at = datetime.now(timezone.utc)
    route_specs = [
        ("origin_to_departure_airport", points[0],
         {"latitude": departure_airport.latitude_deg, "longitude": departure_airport.longitude_deg}, origin_drive_at),
        ("arrival_airport_to_destination", {"latitude": arrival_airport.latitude_deg, "longitude": arrival_airport.longitude_deg},
         points[1], arrival_utc),
    ]
    legs = []
    for leg_name, leg_origin, leg_destination, leg_departure in route_specs:
        allowed, block, reservation = reserve_google_maps_call(session, settings, "routes_traffic_aware",
            fingerprint(f"{base_fingerprint}:{leg_name}"), call_count, request_limit)
        if not allowed:
            return {"status": "blocked", "reason": block, "calls_used": call_count, "legs": legs,
                    "message": "Door-to-door calculation stopped at its configured quota or cost limit."}
        call_count += 1
        try:
            route = await compute_route(leg_origin, leg_destination, leg_departure,
                settings.google_maps_key, settings.google_maps_timeout_seconds)
            finish_search_call(session, reservation, "success")
            traffic_mode = "current_traffic" if (leg_departure - datetime.now(timezone.utc)).total_seconds() <= 900 else "future_prediction"
            legs.append({"kind": leg_name, **route, "departure_time": leg_departure.isoformat(),
                         "traffic_mode": traffic_mode,
                         "provider": "Google Maps Routes API", "retrieved_at": datetime.now(timezone.utc).isoformat()})
        except (httpx.HTTPError, ValueError, KeyError, TypeError, MapsProviderError) as error:
            finish_search_call(session, reservation, getattr(error, "reason", "provider_error"))
            return {"status": "partial", "reason": getattr(error, "reason", "provider_error"),
                    "calls_used": call_count, "legs": legs,
                    "message": "A ground leg could not be estimated. Door-to-door duration is incomplete."}

    origin_minutes = math.ceil(legs[0]["duration_seconds"] / 60)
    destination_minutes = math.ceil(legs[1]["duration_seconds"] / 60)
    origin_schedule_window = math.ceil((departure_utc - origin_drive_at).total_seconds() / 60)
    timing = calculate_door_to_door_timing(origin_minutes, origin_schedule_window,
        scheduled_flight_minutes, destination_minutes)
    risks = ["Ground transport fares are unavailable.", "Airport access time uses a configured check-in buffer."]
    if origin_schedule_window < settings.airport_checkin_buffer_minutes:
        risks.append("Less than the configured airport check-in buffer remains before departure.")
    if origin_minutes > origin_schedule_window:
        risks.append("The origin ground estimate exceeds the configured airport check-in buffer.")
    if abs(scheduled_flight_minutes - request.flight_duration_minutes) > 120:
        risks.append("Provider flight duration differs from the elapsed time between its local schedule timestamps.")
    feasible = timing.feasible_for_scheduled_departure
    return {"status": "ready" if feasible else "infeasible", "legs": legs,
            "departure_airport": request.departure_airport_code.upper(),
            "arrival_airport": request.arrival_airport_code.upper(),
            "flight_duration_minutes": request.flight_duration_minutes,
            "scheduled_flight_elapsed_minutes": scheduled_flight_minutes,
            "airport_checkin_buffer_minutes": settings.airport_checkin_buffer_minutes,
            "origin_ground_minutes": origin_minutes, "destination_ground_minutes": destination_minutes,
            "estimated_total_minutes": timing.total_minutes,
            "estimated_wait_at_departure_airport_minutes": timing.airport_wait_minutes,
            "estimated_total_known_cost": None,
            "unpriced_components": ["origin ground transfer", "destination ground transfer"],
            "feasible_for_scheduled_departure": feasible,
            "risks": risks,
            "message": None if feasible else "The origin transfer is expected to reach the airport after the scheduled departure.",
            "source": "Google Maps Routes API + SerpApi Google Flights",
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "calls_used": call_count}


def eligible(airport: Airport) -> bool:
    return airport.type in ELIGIBLE_TYPES and airport.scheduled_service is True


def as_record(airport: Airport, distance_km: float | None = None) -> AirportRecord:
    is_eligible = eligible(airport)
    if airport.scheduled_service is True:
        note = "OurAirports marks this airport as having scheduled service; verify passenger service with the provider."
    elif airport.scheduled_service is False:
        note = "OurAirports marks no scheduled service."
    else:
        note = "Scheduled-service status is unknown in OurAirports."
    if airport.type not in ELIGIBLE_TYPES:
        note += " Airport type is not a passenger airport type."
    return AirportRecord.model_validate({
        "id": airport.id, "name": airport.name, "municipality": airport.municipality,
        "iso_country": airport.iso_country, "type": airport.type, "iata_code": airport.iata_code,
        "icao_code": airport.icao_code, "latitude_deg": airport.latitude_deg,
        "longitude_deg": airport.longitude_deg, "scheduled_service": airport.scheduled_service,
        "passenger_service_eligible": is_eligible, "eligibility_note": note, "distance_km": distance_km,
    })


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1, a)))


@app.get("/health")
def health():
    return {"status": "ok", "airport_data": SOURCE, "source_retrieved_on": DATASET_RETRIEVED_ON}


@app.get("/api/providers/flight-search")
def flight_search_status(session: Session = Depends(get_session)):
    settings = get_settings()
    readiness = provider_readiness(settings, session)
    return {
        "provider": "SerpApi Google Flights", "status": readiness["status"],
        "reason": readiness["reason"], "limits": readiness["limits"],
        "month_calls_used": readiness.get("month_calls_used", 0),
        "day_calls_used": readiness.get("day_calls_used", 0),
    }


@app.post("/api/flights/search", response_model=FlightSearchResponse)
async def search_flights(request: FlightSearchRequest, session: Session = Depends(get_session)):
    settings = get_settings()
    readiness = provider_readiness(settings, session)
    if readiness["status"] != "ready":
        return FlightSearchResponse(
            status="unavailable" if readiness["status"] == "unavailable" else "blocked",
            reason=readiness["reason"],
            message=("Live flight search is unavailable because the provider is not configured. No flight request was made."
                     if readiness["status"] == "unavailable" else
                     "Live flight search is blocked by request or cost limits. No flight request was made."),
            calls_allowed=settings.max_flight_searches_per_user_search,
        )

    origin_matches = airport_candidates(session, request.origin)
    destination_matches = airport_candidates(session, request.destination)
    if not origin_matches or not destination_matches:
        missing = "origin" if not origin_matches else "destination"
        return FlightSearchResponse(
            status="unavailable", reason=f"{missing}_airport_not_found",
            message=f"No OurAirports airport marked with scheduled service could be matched to the {missing}.",
            calls_allowed=settings.max_flight_searches_per_user_search,
        )

    origins = expand_nearby_airports(session, origin_matches, request.include_nearby_airports)
    destinations = expand_nearby_airports(session, destination_matches, request.include_nearby_airports)

    pairs, omitted = airport_pair_shortlist(
        origins, destinations, request.include_nearby_airports,
        settings.max_flight_searches_per_user_search,
    )
    if not pairs:
        return FlightSearchResponse(
            status="blocked", reason="no_distinct_airport_pairs",
            message="No eligible distinct airport pairs are available for this search.",
            calls_allowed=settings.max_flight_searches_per_user_search,
        )

    results = []
    searched_pairs = []
    failed_pairs = []
    not_searched_pairs = []
    call_errors = []
    any_cached = False
    retrieved_at = None
    calls_used = 0
    for index, (origin, destination) in enumerate(pairs):
        params = params_for_search(request, origin.iata_code, destination.iata_code, settings)
        fingerprint = request_fingerprint(params)
        allowed, reason, reservation = reserve_search_call(session, settings, fingerprint, calls_used)
        pair = {"origin": origin.iata_code, "destination": destination.iata_code}
        if not allowed:
            not_searched_pairs.extend([pair, *[
                {"origin": a.iata_code, "destination": b.iata_code} for a, b in pairs[index + 1:]
            ], *[{"origin": a.iata_code, "destination": b.iata_code} for a, b in omitted]])
            return FlightSearchResponse(
                status="blocked", reason=reason,
                message=(f"Search stopped after {calls_used} provider request(s) at the configured limit. Any listed results came from those provider responses."
                         if calls_used else "Search blocked by configured quota and cost controls; no provider request was made."),
                results=results, airport_pairs_searched=searched_pairs, airport_pairs_failed=failed_pairs,
                airport_pairs_not_searched=not_searched_pairs, calls_used=calls_used,
                calls_allowed=settings.max_flight_searches_per_user_search,
                retrieved_at=retrieved_at,
            )

        calls_used += 1
        try:
            payload = await search_serpapi(params, settings.serpapi_key, settings.request_timeout_seconds)
            retrieved_at = datetime.now(timezone.utc)
            offers, cached = normalize_response(payload, request, origin, destination, retrieved_at)
            results.extend(offers)
            any_cached = any_cached or cached
            finish_search_call(session, reservation, "cached" if cached else "success")
            searched_pairs.append(pair)
        except ProviderError as error:
            finish_search_call(session, reservation, error.reason)
            call_errors.append(error.reason)
            failed_pairs.append({**pair, "reason": error.reason})
            not_searched_pairs.extend([
                {"origin": a.iata_code, "destination": b.iata_code} for a, b in pairs[index + 1:]
            ])
            break
        except httpx.TimeoutException:
            finish_search_call(session, reservation, "timeout")
            call_errors.append("provider_timeout")
            failed_pairs.append({**pair, "reason": "provider_timeout"})
            not_searched_pairs.extend([
                {"origin": a.iata_code, "destination": b.iata_code} for a, b in pairs[index + 1:]
            ])
            break
        except httpx.RequestError:
            finish_search_call(session, reservation, "network_error")
            call_errors.append("provider_network_error")
            failed_pairs.append({**pair, "reason": "provider_network_error"})
            not_searched_pairs.extend([
                {"origin": a.iata_code, "destination": b.iata_code} for a, b in pairs[index + 1:]
            ])
            break
        except (ValueError, TypeError, KeyError, AttributeError):
            finish_search_call(session, reservation, "invalid_provider_response")
            call_errors.append("invalid_provider_response")
            failed_pairs.append({**pair, "reason": "invalid_provider_response"})
            not_searched_pairs.extend([{
                "origin": a.iata_code, "destination": b.iata_code
            } for a, b in pairs[index + 1:]])
            break

    not_searched_pairs.extend({"origin": a.iata_code, "destination": b.iata_code} for a, b in omitted)
    not_searched_pairs = list({(pair["origin"], pair["destination"]): pair for pair in not_searched_pairs}.values())
    if call_errors:
        return FlightSearchResponse(
            status="error", reason=call_errors[0],
            message="The flight provider could not complete the full search. Any results shown were returned before the provider error.",
            results=results, airport_pairs_searched=searched_pairs, airport_pairs_failed=failed_pairs,
            airport_pairs_not_searched=not_searched_pairs, calls_used=calls_used,
            calls_allowed=settings.max_flight_searches_per_user_search, retrieved_at=retrieved_at,
        )
    status = "cached" if any_cached and all(result.status == "cached" for result in results) else "live"
    if results:
        message = "Flight results returned by SerpApi. Fares and availability can change before booking."
    elif not_searched_pairs:
        message = "The provider returned no flight options for the pairs searched. Additional airport combinations were skipped to respect your configured request cap."
    else:
        message = "The provider returned no flight options for the searched airport pairs."
    return FlightSearchResponse(
        status=status, message=message, results=results,
        airport_pairs_searched=searched_pairs, airport_pairs_failed=failed_pairs,
        airport_pairs_not_searched=not_searched_pairs,
        calls_used=calls_used, calls_allowed=settings.max_flight_searches_per_user_search,
        retrieved_at=retrieved_at,
    )


@app.get("/api/airports", response_model=AirportResults)
def search_airports(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    scheduled_service_only: bool = True,
    session: Session = Depends(get_session),
):
    term = q.strip()
    if len(term) < 2:
        raise HTTPException(422, "Search must contain at least two non-space characters.")
    # City names can be alternate forms such as "New Delhi", so municipality
    # search accepts an interior match while names and codes remain prefix based.
    pattern = f"{term}%"
    city_pattern = f"%{term}%"
    statement = select(Airport).where(or_(
        Airport.name.ilike(pattern), Airport.municipality.ilike(city_pattern),
        Airport.iata_code.ilike(pattern), Airport.icao_code.ilike(pattern),
    ))
    if scheduled_service_only:
        statement = statement.where(Airport.scheduled_service.is_(True), Airport.type.in_(ELIGIBLE_TYPES))
    matches = session.scalars(statement).all()
    matches.sort(key=lambda a: (0 if a.iata_code and a.iata_code.lower() == term.lower() else 1,
                                0 if eligible(a) else 1, (a.municipality or "").casefold(), a.name.casefold()))
    results = [as_record(airport) for airport in matches[:limit]]
    return AirportResults(results=results, total=len(results))


@app.get("/api/airports/iata/{iata_code}", response_model=AirportRecord)
def airport_by_iata(iata_code: str, session: Session = Depends(get_session)):
    code = iata_code.strip().upper()
    if len(code) != 3 or not code.isalpha():
        raise HTTPException(422, "IATA code must be exactly three letters.")
    airport = session.scalar(select(Airport).where(Airport.iata_code == code))
    if airport is None:
        raise HTTPException(404, f"No OurAirports record found for IATA code {code}.")
    return as_record(airport)


@app.get("/api/airports/nearby", response_model=AirportResults)
def nearby_airports(
    lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180),
    radius_km: float = Query(default=250, gt=0, le=1000),
    limit: int = Query(default=20, ge=1, le=100),
    scheduled_service_only: bool = True,
    session: Session = Depends(get_session),
):
    statement = select(Airport).where(Airport.latitude_deg.is_not(None), Airport.longitude_deg.is_not(None))
    if scheduled_service_only:
        statement = statement.where(Airport.scheduled_service.is_(True), Airport.type.in_(ELIGIBLE_TYPES))
    nearby = []
    for airport in session.scalars(statement):
        distance = haversine_km(lat, lon, airport.latitude_deg, airport.longitude_deg)
        if distance <= radius_km:
            nearby.append((distance, airport))
    nearby.sort(key=lambda pair: (pair[0], pair[1].name.casefold()))
    results = [as_record(airport, round(distance, 2)) for distance, airport in nearby[:limit]]
    return AirportResults(results=results, total=len(results))


@app.get("/api/rail/status")
def rail_provider_status():
    return {
        "provider": "Indian Railways / IRCTC",
        "status": "unavailable",
        "reason": "no_authorized_live_provider",
        "message": "Live train schedules, fares, and seat availability require an approved provider connection.",
        "station_reference": {
            "source": STATION_SOURCE,
            "source_url": STATION_SOURCE_URL,
            "retrieved_on": STATION_RETRIEVED_ON.isoformat(),
        },
        "official_enquiry": {"ntes": NTES_URL, "irctc": IRCTC_URL},
        "live_requests_enabled": False,
    }


@app.get("/api/rail/stations")
def search_rail_stations(q: str = Query(min_length=2, max_length=100), limit: int = Query(default=10, ge=1, le=25)):
    term = q.strip()
    if len(term) < 2:
        raise HTTPException(422, "Station search must contain at least two non-space characters.")
    results = find_stations(term, limit)
    return {
        "results": [station.__dict__ | {"retrieved_on": station.retrieved_on.isoformat()} for station in results],
        "total": len(results),
        "source": STATION_SOURCE,
        "source_url": STATION_SOURCE_URL,
        "retrieved_on": STATION_RETRIEVED_ON.isoformat(),
    }


class RailSearchRequest(BaseModel):
    origin_code: str = Field(pattern=r"^[A-Za-z0-9]{2,7}$")
    destination_code: str = Field(pattern=r"^[A-Za-z0-9]{2,7}$")
    journey_date: date


@app.post("/api/rail/search")
def search_rail_journeys(request: RailSearchRequest):
    origin_code = request.origin_code.upper()
    destination_code = request.destination_code.upper()
    # Exact route validation uses the complete official reference, not a guessed code.
    from .rail import load_stations
    all_stations = {station.code: station for station in load_stations()}
    origin = all_stations.get(origin_code)
    destination = all_stations.get(destination_code)
    if origin is None or destination is None:
        raise HTTPException(404, "Choose origin and destination from the Indian Railways station list.")
    if origin_code == destination_code:
        raise HTTPException(422, "Origin and destination stations must be different.")
    if request.journey_date < date.today():
        raise HTTPException(422, "Journey date cannot be in the past.")
    return {
        "status": "unavailable",
        "reason": "no_authorized_live_provider",
        "message": "FDR cannot retrieve a current train schedule for this route yet. Check the official railway enquiry before planning around a train.",
        "origin": {"name": origin.name, "code": origin.code},
        "destination": {"name": destination.name, "code": destination.code},
        "journey_date": request.journey_date.isoformat(),
        "results": [],
        "availability": "unavailable",
        "fare": "unavailable",
        "retrieved_at": None,
        "fallbacks": [
            {"name": "National Train Enquiry System (NTES)", "url": NTES_URL},
            {"name": "IRCTC train search and availability", "url": IRCTC_URL},
        ],
    }
