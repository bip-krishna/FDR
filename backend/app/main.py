import math
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Airport

SOURCE = "OurAirports"
DATASET_RETRIEVED_ON = date(2026, 10, 24)
ELIGIBLE_TYPES = {"large_airport", "medium_airport", "small_airport"}
EARTH_RADIUS_KM = 6371.0088

app = FastAPI(title="FDR Airport Discovery API", version="0.2.0")


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
