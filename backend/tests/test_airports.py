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
            Airport(source_id="fixture-6", ident="TEST6", type="medium_airport", name="Other City Airport",
                    latitude_deg=1.5, longitude_deg=0.0, iso_country="ZZ", municipality="Other City",
                    scheduled_service=True, icao_code="TST6", iata_code="CCC"),
        ])

    def override_session():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        test_client.app.state.test_session_factory = TestSession
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


def set_provider_ready(monkeypatch):
    for key, value in {
        "ENABLE_SERPAPI": "true", "SERPAPI_API_KEY": "test-key",
        "MAX_EXTERNAL_API_CALLS_PER_DAY": "5", "MAX_EXTERNAL_API_CALLS_PER_MONTH": "50",
        "MAX_FLIGHT_SEARCHES_PER_USER_SEARCH": "2", "SERPAPI_MAX_CALLS_PER_DAY": "5",
        "SERPAPI_MAX_CALLS_PER_MONTH": "50", "SERPAPI_COST_PER_SEARCH_INR": "0",
        "MONTHLY_EXTERNAL_API_BUDGET_INR": "0",
    }.items():
        monkeypatch.setenv(key, value)


def future_date():
    from datetime import date, timedelta
    return (date.today() + timedelta(days=14)).isoformat()


def test_missing_credentials_returns_unavailable_without_provider_call(client, monkeypatch):
    monkeypatch.setenv("ENABLE_SERPAPI", "false")
    monkeypatch.setenv("SERPAPI_API_KEY", "")
    response = client.post("/api/flights/search", json={
        "origin": "AAA", "destination": "BBB", "departure_date": future_date(),
    })
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["reason"] == "provider_disabled"
    assert response.json()["results"] == []


def test_live_search_normalizes_provider_results_and_records_usage(client, monkeypatch):
    from datetime import datetime, timezone
    from app import main
    from app.models import ProviderUsage

    set_provider_ready(monkeypatch)
    calls = []

    async def fake_search(params, api_key, timeout):
        calls.append((params, api_key))
        return {
            "search_metadata": {
                "status": "Success", "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "google_flights_url": "https://www.google.com/travel/flights?hl=en#test",
            },
            "best_flights": [{
                "flights": [{
                    "airline": "Example Air", "flight_number": "EX 101", "duration": 90,
                    "departure_airport": {"name": "Central Airport", "id": "AAA", "time": "2030-04-02 09:00"},
                    "arrival_airport": {"name": "Nearby Airport", "id": "BBB", "time": "2030-04-02 10:30"},
                }],
                "total_duration": 90,
            }],
        }

    monkeypatch.setattr(main, "search_serpapi", fake_search)
    response = client.post("/api/flights/search", json={
        "origin": "AAA", "destination": "BBB", "departure_date": future_date(),
        "currency": "inr",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "live"
    assert data["calls_used"] == 1
    assert data["airport_pairs_searched"] == [{"origin": "AAA", "destination": "BBB"}]
    offer = data["results"][0]
    assert offer["currency"] == "INR"
    assert offer["price"] is None
    assert offer["stops"] == 0
    assert offer["segments"][0]["flight_number"] == "EX 101"
    assert offer["source"] == "SerpApi Google Flights"
    assert offer["booking_url"].startswith("https://www.google.com/travel/flights")
    assert calls[0][0]["type"] == 2
    assert calls[0][1] == "test-key"
    with client.app.state.test_session_factory() as session:
        usage = session.query(ProviderUsage).one()
        assert usage.provider == "serpapi"
        assert usage.status == "success"


def test_provider_disabled_or_zero_limits_never_call_upstream(client, monkeypatch):
    from app import main

    set_provider_ready(monkeypatch)
    monkeypatch.setenv("MAX_EXTERNAL_API_CALLS_PER_MONTH", "0")

    async def unexpected_search(*_args, **_kwargs):
        raise AssertionError("Provider must not be called when global limits are zero")

    monkeypatch.setattr(main, "search_serpapi", unexpected_search)
    response = client.post("/api/flights/search", json={
        "origin": "AAA", "destination": "BBB", "departure_date": future_date(),
    })
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["reason"] == "global_request_limits_not_configured"


def test_nearby_flight_search_stays_within_configured_pair_limit(client, monkeypatch):
    from app import main

    set_provider_ready(monkeypatch)
    monkeypatch.setenv("MAX_FLIGHT_SEARCHES_PER_USER_SEARCH", "1")
    calls = []

    async def fake_search(params, api_key, timeout):
        calls.append(params)
        return {"search_metadata": {"status": "Success"}, "best_flights": [], "other_flights": []}

    monkeypatch.setattr(main, "search_serpapi", fake_search)
    response = client.post("/api/flights/search", json={
        "origin": "Sample City", "destination": "Other City",
        "departure_date": future_date(), "include_nearby_airports": True,
    })
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "live"
    assert data["calls_used"] == 1
    assert len(calls) == 1
    assert len(data["airport_pairs_searched"]) == 1
    assert len(data["airport_pairs_not_searched"]) >= 1
    assert "respect your configured request cap" in data["message"]


def test_provider_errors_are_labeled_separately_from_unsearched_pairs(client, monkeypatch):
    from app import main
    from app.flights import ProviderError

    set_provider_ready(monkeypatch)

    async def rate_limited_search(*_args, **_kwargs):
        raise ProviderError("provider_rate_limited")

    monkeypatch.setattr(main, "search_serpapi", rate_limited_search)
    response = client.post("/api/flights/search", json={
        "origin": "AAA", "destination": "BBB", "departure_date": future_date(),
    })
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "error"
    assert data["airport_pairs_failed"] == [{
        "origin": "AAA", "destination": "BBB", "reason": "provider_rate_limited",
    }]
    assert data["airport_pairs_not_searched"] == []


def test_future_date_and_distinct_route_are_required(client):
    response = client.post("/api/flights/search", json={
        "origin": "AAA", "destination": "AAA", "departure_date": future_date(),
    })
    assert response.status_code == 422
    response = client.post("/api/flights/search", json={
        "origin": "AAA", "destination": "BBB", "departure_date": "2020-01-01",
    })
    assert response.status_code == 422
