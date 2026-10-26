from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_session
from app.rail import find_stations, load_stations, normalize_rail_segment


def test_official_station_index_supports_name_and_code_search():
    stations = load_stations()
    assert len(stations) > 700
    assert any(station.name == "NEW DELHI" and station.code == "NDLS" for station in stations)
    assert find_stations("NDLS", 1)[0].code == "NDLS"
    assert find_stations("bengaluru", 1)[0].name == "BENGALURU CANTT."
    assert find_stations("x", 10) == []


def test_rail_segment_normalization_keeps_fare_and_availability_unknown():
    segment = normalize_rail_segment({
        "train_number": "12345", "train_name": "Example Express",
        "origin_code": "ndls", "destination_code": "HWH",
        "departure_time": "2027-01-01T10:00:00+05:30",
        "arrival_time": "2027-01-01T22:00:00+05:30", "travel_classes": ["3A", "SL", "3A"],
    }, provider="approved-test-adapter", retrieved_at=datetime.now(timezone.utc))
    assert segment["duration_minutes"] == 720
    assert segment["origin_code"] == "NDLS"
    assert segment["travel_classes"] == ["3A", "SL"]
    assert segment["fare"] is None
    assert segment["availability"] == "unavailable"


def test_segment_rejects_naive_or_inconsistent_schedule_times():
    base = {
        "train_number": "12345", "origin_code": "NDLS", "destination_code": "HWH",
        "departure_time": "2027-01-01T10:00:00", "arrival_time": "2027-01-01T09:00:00",
    }
    with pytest.raises(ValueError):
        normalize_rail_segment(base, provider="adapter", retrieved_at=datetime.now(timezone.utc))


@pytest.fixture
def client():
    def no_database_session():
        yield None

    app.dependency_overrides[get_session] = no_database_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_station_endpoint_returns_reference_provenance(client):
    response = client.get("/api/rail/stations", params={"q": "New Delhi"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["code"] == "NDLS"
    assert payload["source"] == "Indian Railways Trains at a Glance 2026 — Station Code Index"
    assert payload["retrieved_on"] == "2026-10-26"


def test_train_search_never_claims_schedule_fare_or_inventory(client):
    response = client.post("/api/rail/search", json={
        "origin_code": "NDLS", "destination_code": "HWH",
        "journey_date": (date.today() + timedelta(days=3)).isoformat(),
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["results"] == []
    assert payload["availability"] == "unavailable"
    assert payload["fare"] == "unavailable"
    assert [item["name"] for item in payload["fallbacks"]] == [
        "National Train Enquiry System (NTES)", "IRCTC train search and availability"
    ]


def test_invalid_station_or_same_station_is_rejected(client):
    future = (date.today() + timedelta(days=1)).isoformat()
    assert client.post("/api/rail/search", json={"origin_code": "ZZZZ", "destination_code": "HWH", "journey_date": future}).status_code == 404
    assert client.post("/api/rail/search", json={"origin_code": "NDLS", "destination_code": "NDLS", "journey_date": future}).status_code == 422
