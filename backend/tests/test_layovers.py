from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.layovers import AttractionCandidate, evaluate_layover
from app.main import app


def test_long_layover_has_conservative_window_and_return_deadline():
    arrival = datetime(2026, 10, 27, 0, 0, tzinfo=timezone.utc)
    result = evaluate_layover(arrival_at=arrival, departure_at=arrival + timedelta(hours=12))
    assert result["long_layover"] is True
    assert result["available_exploration_minutes"] == 480
    assert result["latest_recommended_airport_return_at"] == "2026-10-27T09:00:00+00:00"
    assert result["airport_exit_authorized"] is False


def test_unknown_exit_eligibility_rejects_candidate():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    result = evaluate_layover(arrival_at=now, departure_at=now + timedelta(hours=14),
        candidates=[AttractionCandidate("p1", "Museum", 30)])
    assert result["feasible_candidates"] == []
    assert result["rejected_candidates"][0]["reason"] == "airport_exit_not_verified"


def test_tight_window_rejects_round_trip_and_visit():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    result = evaluate_layover(arrival_at=now, departure_at=now + timedelta(hours=11),
        airport_return_buffer_minutes=300, terminal_transfer_buffer_minutes=240,
        exit_eligibility="verified_yes",
        candidates=[AttractionCandidate("p1", "Museum", 100, 45)])
    assert result["rejected_candidates"][0]["reason"] == "insufficient_conservative_time"


def test_opening_window_and_opening_hours_are_checked():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    result = evaluate_layover(arrival_at=now, departure_at=now + timedelta(hours=14),
        exit_eligibility="verified_yes", candidates=[AttractionCandidate(
            "p1", "Museum", 30, 60, opens_at=now + timedelta(hours=3),
            closes_at=now + timedelta(hours=8))])
    assert result["rejected_candidates"][0]["reason"] == "place_not_open_at_arrival"


def test_api_requires_timezone_aware_timestamps_and_returns_unverified_warning():
    with TestClient(app) as client:
        bad = client.post("/api/layovers/evaluate", json={
            "arrival_at": "2026-10-27T01:00:00", "departure_at": "2026-10-27T13:00:00"})
        assert bad.status_code == 422
        good = client.post("/api/layovers/evaluate", json={
            "arrival_at": "2026-10-27T01:00:00+05:30",
            "departure_at": "2026-10-27T13:00:00+05:30"})
    assert good.status_code == 200
    payload = good.json()
    assert payload["long_layover"] is True
    assert payload["exit_eligibility"] == "unknown"
    assert payload["airport_exit_authorized"] is False
    assert payload["places_status"] == "unavailable"
