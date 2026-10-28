import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.groq_layover import (
    InvalidItinerary, LayoverPlanRequest, ModelSelection, PlanConstraints,
    VerifiedPlace, plan_with_verified_candidates,
    validate_model_selection,
)
from app.main import app
from app.usage import finish_search_call, reserve_groq_layover_call


def setup_candidate(now):
    return VerifiedPlace(candidate_id="place-1", name="City Museum", source="Google Places",
        source_status="live", opening_status="verified", traffic_status="verified",
        airport_to_place_minutes=40, place_to_airport_minutes=50, visit_minutes=90,
        opens_at=now + timedelta(hours=1), closes_at=now + timedelta(hours=10),
        known_cost_amount=None, known_cost_currency=None)


def setup_constraints(now):
    return PlanConstraints(arrival_at=now, departure_at=now + timedelta(hours=12),
        exploration_start_at=now + timedelta(hours=1),
        latest_return_at=now + timedelta(hours=9), exit_eligibility_verified=True)


def test_ai_selection_cannot_invent_place_ids_or_schedule_facts():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    candidate = setup_candidate(now)
    constraints = setup_constraints(now)
    selection = ModelSelection(ordered_candidate_ids=["place-unknown"])
    with pytest.raises(InvalidItinerary, match="not supplied"):
        validate_model_selection(selection, [candidate], constraints, max_places=1)


def test_candidate_without_verified_traffic_or_opening_hours_is_rejected():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    candidate = setup_candidate(now).model_copy(update={"traffic_status": "unavailable"})
    with pytest.raises(InvalidItinerary, match="opening hours and traffic"):
        from app.groq_layover import validate_candidate
        validate_candidate(candidate, setup_constraints(now))


def test_ai_selected_candidate_gets_backend_computed_times_and_keeps_unknown_cost():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    candidate = setup_candidate(now)
    constraints = setup_constraints(now)
    selection = ModelSelection(ordered_candidate_ids=["place-1"])
    result = validate_model_selection(selection, [candidate], constraints, max_places=1)
    assert result["places"][0]["return_to_airport_at"] == "2026-10-27T04:00:00+00:00"
    assert result["places"][0]["known_cost_amount"] is None
    assert "verified candidate list" in result["places"][0]["explanation"]
    assert result["airport_exit_authorized"] is False


def test_empty_model_selection_is_not_rendered_as_a_ready_plan():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    result = validate_model_selection(ModelSelection(ordered_candidate_ids=[]),
        [setup_candidate(now)], setup_constraints(now), max_places=1)
    assert result["status"] == "unavailable"
    assert result["reason"] == "no_candidate_selected"


def test_missing_verified_candidates_never_reserves_or_calls_groq():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    request = LayoverPlanRequest(arrival_at=now, departure_at=now + timedelta(hours=12),
        exit_eligibility="verified_yes", disclaimer_acknowledged=True)

    def forbidden(*_args):
        raise AssertionError("No request or reservation is allowed without candidates")

    result = asyncio.run(plan_with_verified_candidates(request=request, candidates=[],
        settings=SimpleNamespace(), session=None, reserve_call=forbidden, finish_call=forbidden))
    assert result["status"] == "unavailable"
    assert result["groq_called"] is False


def test_verified_candidate_uses_groq_selection_then_revalidates():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    request = LayoverPlanRequest(arrival_at=now, departure_at=now + timedelta(hours=12),
        exit_eligibility="verified_yes", disclaimer_acknowledged=True, interests=["history"])
    candidate = setup_candidate(now)
    usage = object()
    calls = []

    def reserve(*args):
        calls.append("reserve")
        return True, None, usage

    def finish(_session, _usage, status):
        calls.append(status)

    async def select(**kwargs):
        assert kwargs["candidates"] == [candidate]
        return ModelSelection(ordered_candidate_ids=["place-1"])

    result = asyncio.run(plan_with_verified_candidates(request=request, candidates=[candidate],
        settings=SimpleNamespace(groq_api_key="key", groq_layover_model="openai/gpt-oss-20b",
            request_timeout_seconds=4), session=object(), reserve_call=reserve,
        finish_call=finish, selection_request=select))
    assert result["status"] == "ready"
    assert result["groq_called"] is True
    assert calls == ["reserve", "success"]


def test_api_requires_disclaimer_acknowledgement_and_never_uses_client_candidates():
    now = "2026-10-27T00:00:00+00:00"
    with TestClient(app) as client:
        unacknowledged = client.post("/api/layovers/plan", json={
            "arrival_at": now, "departure_at": "2026-10-27T12:00:00+00:00"})
        missing = client.post("/api/layovers/plan", json={
            "arrival_at": now, "departure_at": "2026-10-27T12:00:00+00:00",
            "exit_eligibility": "verified_yes", "disclaimer_acknowledged": True,
            "candidates": [{"candidate_id": "fake"}]})
    assert unacknowledged.status_code == 200
    assert unacknowledged.json()["reason"] == "disclaimer_not_acknowledged"
    assert missing.status_code == 422


def test_groq_quota_reservation_enforces_per_layover_cap():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    settings = SimpleNamespace(groq_layover_enabled=True, groq_api_key="key",
        groq_layover_model="openai/gpt-oss-20b", max_external_calls_day=10,
        max_external_calls_month=100, groq_daily_limit=5, groq_monthly_limit=20,
        groq_max_calls_per_layover=1, groq_cost_per_call_inr=0.0,
        monthly_external_budget_inr=0.0)
    ok, reason, usage = reserve_groq_layover_call(session, settings, "same-layover")
    assert ok and reason is None and usage is not None
    finish_search_call(session, usage, "success")
    ok, reason, usage = reserve_groq_layover_call(session, settings, "same-layover")
    assert not ok and reason == "per_layover_request_limit_reached" and usage is None
    session.close()
    engine.dispose()


def test_groq_request_uses_strict_json_schema(monkeypatch):
    import asyncio
    import json
    from app import groq_layover

    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    candidate = setup_candidate(now)
    constraints = setup_constraints(now)
    captured = {}

    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return {"choices": [{"message": {"content": json.dumps({
                "ordered_candidate_ids": ["place-1"],
            })}}]}

    class Client:
        def __init__(self, timeout):
            captured["timeout"] = timeout
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_args):
            return None
        async def post(self, url, headers, json):
            captured.update(url=url, headers=headers, body=json)
            return Response()

    monkeypatch.setattr(groq_layover.httpx, "AsyncClient", Client)
    selection = asyncio.run(groq_layover.request_groq_selection(api_key="secret", model="openai/gpt-oss-20b",
        timeout=3, interests=["history"], candidates=[candidate], constraints=constraints, max_places=1))
    assert selection.ordered_candidate_ids == ["place-1"]
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["body"]["response_format"]["json_schema"]["strict"] is True
    prompt = captured["body"]["messages"][1]["content"]
    assert "place-1" in prompt
    assert "secret" not in prompt
