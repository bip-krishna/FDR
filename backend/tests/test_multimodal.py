from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.multimodal import TravelSegment, optimize_itineraries


BASE = datetime(2027, 1, 1, 8, tzinfo=timezone.utc)


def segment(segment_id, mode, origin, destination, depart_minutes, duration_minutes, fare=None,
            currency=None, ticket=None, data_status="live", provider="isolated fixture"):
    return TravelSegment(
        segment_id=segment_id, mode=mode, origin=origin, destination=destination,
        departure_at=BASE + timedelta(minutes=depart_minutes),
        arrival_at=BASE + timedelta(minutes=depart_minutes + duration_minutes),
        provider=provider, data_status=data_status,
        fare_amount=Decimal(str(fare)) if fare is not None else None,
        currency=currency, ticket_group_id=ticket,
    )


def test_mixed_flight_ground_path_is_time_ordered_and_marks_missing_costs():
    route = optimize_itineraries("city:a", "city:c", [
        segment("f1", "flight", "city:a", "airport:b", 0, 60, 100, "INR", "ticket-1"),
        segment("g1", "ground", "airport:b", "city:c", 90, 30, data_status="estimated", provider="Maps fixture"),
    ])
    assert route["status"] == "ready"
    option = route["routes"][0]
    assert option["segment_ids"] == ["f1", "g1"]
    assert option["duration_minutes"] == 120
    assert option["fare_amount"] is None
    assert option["known_fare_amount"] == "100"
    assert option["known_fare_currency"] == "INR"
    assert option["confirmed_bookable"] is False
    assert any("separate tickets" in risk for risk in option["risks"])
    assert any("Ground transfer times are estimates" in risk for risk in option["risks"])


def test_flight_connection_requires_transfer_buffer_and_separate_ticket_warning():
    first = segment("first", "flight", "A", "B", 0, 60, 100, "INR", "one")
    too_soon = segment("soon", "flight", "B", "C", 179, 60, 100, "INR", "two")
    enough = segment("enough", "flight", "B", "C", 180, 60, 100, "INR", "three")
    result = optimize_itineraries("A", "C", [first, too_soon, enough])
    assert [route["segment_ids"] for route in result["routes"]] == [["first", "enough"]]
    assert any("separate tickets" in risk for risk in result["routes"][0]["risks"])


def test_pareto_frontier_preserves_time_cost_tradeoffs_and_removes_dominated_route():
    options = [
        segment("fast", "flight", "A", "D", 0, 240, 500, "INR", "fast"),
        segment("cheap-1", "flight", "A", "B", 0, 90, 200, "INR", "part-1"),
        segment("cheap-2", "flight", "B", "D", 210, 90, 200, "INR", "part-2"),
        segment("worse", "flight", "A", "D", 0, 300, 700, "INR", "worse"),
    ]
    result = optimize_itineraries("A", "D", options)
    routes = {tuple(route["segment_ids"]): route for route in result["routes"]}
    assert routes[("fast",)]["pareto_efficient"] is True
    assert routes[("cheap-1", "cheap-2")]["pareto_efficient"] is True
    assert routes[("worse",)]["pareto_efficient"] is False


def test_incomparable_currencies_and_unknown_fares_are_not_ranked_as_cheaper():
    result = optimize_itineraries("A", "D", [
        segment("inr", "flight", "A", "D", 0, 120, 100, "INR", "1"),
        segment("usd", "flight", "A", "D", 0, 120, 20, "USD", "2"),
        segment("unknown", "flight", "A", "D", 0, 120),
    ])
    assert all(route["pareto_efficient"] for route in result["routes"])
    by_id = {route["segment_ids"][0]: route for route in result["routes"]}
    assert by_id["inr"]["fare_amount"] == "100"
    assert by_id["usd"]["fare_amount"] == "20"
    assert by_id["unknown"]["fare_amount"] is None
    mixed = optimize_itineraries("A", "D", [
        segment("inr-leg", "flight", "A", "B", 0, 30, 100, "INR"),
        segment("usd-leg", "flight", "B", "D", 150, 30, 20, "USD"),
    ])
    assert mixed["routes"][0]["known_fare_amount"] is None
    assert mixed["routes"][0]["known_fare_currency"] is None


def test_invalid_or_naive_schedule_data_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        optimize_itineraries("A", "D", [TravelSegment(
            segment_id="bad", mode="flight", origin="A", destination="D",
            departure_at=datetime(2027, 1, 1, 8), arrival_at=datetime(2027, 1, 1, 10),
            provider="fixture", data_status="live",
        )])


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_optimize_api_returns_route_without_confirming_bookability(client):
    response = client.post("/api/journeys/optimize", json={
        "origin": "city:a", "destination": "city:b",
        "segments": [{
            "segment_id": "flight-1", "mode": "flight", "origin": "city:a", "destination": "city:b",
            "departure_at": "2027-01-01T08:00:00Z", "arrival_at": "2027-01-01T10:00:00Z",
            "provider": "isolated test fixture", "data_status": "live", "fare_amount": 100, "currency": "INR",
        }],
    })
    assert response.status_code == 200
    option = response.json()["routes"][0]
    assert option["duration_minutes"] == 120
    assert option["fare_amount"] == "100"
    assert option["confirmed_bookable"] is False


def test_optimize_api_rejects_timezone_naive_segments(client):
    response = client.post("/api/journeys/optimize", json={
        "origin": "A", "destination": "D",
        "segments": [{
            "segment_id": "bad", "mode": "train", "origin": "A", "destination": "D",
            "departure_at": "2027-01-01T08:00:00", "arrival_at": "2027-01-01T10:00:00",
            "provider": "fixture", "data_status": "static",
        }],
    })
    assert response.status_code == 422
