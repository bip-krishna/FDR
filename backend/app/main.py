import math
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
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


def get_session():
    with SessionLocal() as session:
        yield session


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
