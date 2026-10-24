import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app, get_session
from app.models import Airport


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(test_engine)
    with TestSession.begin() as session:
        session.add_all([
            Airport(source_id="fixture-1", ident="TEST1", type="large_airport", name="Central Airport",
                    latitude_deg=0.0, longitude_deg=0.0, iso_country="ZZ", municipality="Sample City",
                    scheduled_service=True, icao_code="TST1", iata_code="AAA"),
            Airport(source_id="fixture-2", ident="TEST2", type="medium_airport", name="Nearby Airport",
                    latitude_deg=0.5, longitude_deg=0.0, iso_country="ZZ", municipality="Sample City",
                    scheduled_service=True, icao_code="TST2", iata_code="BBB"),
            Airport(source_id="fixture-3", ident="TEST3", type="small_airport", name="Private Field",
                    latitude_deg=0.1, longitude_deg=0.0, iso_country="ZZ", municipality="Sample City",
                    scheduled_service=False, icao_code=None, iata_code=None),
            Airport(source_id="fixture-4", ident="TEST4", type="heliport", name="City Heliport",
                    latitude_deg=0.01, longitude_deg=0.0, iso_country="ZZ", municipality="Sample City",
                    scheduled_service=True, icao_code=None, iata_code=None),
            Airport(source_id="fixture-5", ident="TEST5", type="large_airport", name="Unknown Service Airport",
                    latitude_deg=None, longitude_deg=None, iso_country="ZZ", municipality="Sample City",
                    scheduled_service=None, icao_code=None, iata_code=None),
        ])

    def override_session():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    test_engine.dispose()


def test_iata_lookup_returns_provenance_and_service_status(client):
    response = client.get("/api/airports/iata/aaa")
    assert response.status_code == 200
    assert response.json()["iata_code"] == "AAA"
    assert response.json()["source"] == "OurAirports"
    assert response.json()["passenger_service_eligible"] is True


def test_invalid_and_missing_iata_codes_are_clear(client):
    assert client.get("/api/airports/iata/XX").status_code == 422
    assert client.get("/api/airports/iata/ZZZ").status_code == 404


def test_city_search_defaults_to_scheduled_passenger_airport_types(client):
    response = client.get("/api/airports", params={"q": "Sample City"})
    assert [row["iata_code"] for row in response.json()["results"]] == ["AAA", "BBB"]


def test_expanded_city_search_keeps_ineligible_records_labeled(client):
    response = client.get("/api/airports", params={"q": "Sample City", "scheduled_service_only": "false"})
    records = response.json()["results"]
    assert {row["name"] for row in records} == {
        "Central Airport", "Nearby Airport", "Private Field", "City Heliport", "Unknown Service Airport"
    }
    by_name = {row["name"]: row for row in records}
    assert by_name["Private Field"]["passenger_service_eligible"] is False
    assert by_name["Unknown Service Airport"]["passenger_service_eligible"] is False
    assert by_name["Unknown Service Airport"]["latitude_deg"] is None


def test_nearby_airports_are_ranked_by_haversine_distance(client):
    response = client.get("/api/airports/nearby", params={"lat": 0, "lon": 0, "radius_km": 100})
    records = response.json()["results"]
    assert [row["iata_code"] for row in records] == ["AAA", "BBB"]
    assert records[0]["distance_km"] == 0
    assert records[1]["distance_km"] == pytest.approx(55.6, abs=0.2)


def test_invalid_geographic_input_is_rejected(client):
    assert client.get("/api/airports/nearby", params={"lat": 91, "lon": 0}).status_code == 422
    assert client.get("/api/airports/nearby", params={"lat": 0, "lon": 181}).status_code == 422
