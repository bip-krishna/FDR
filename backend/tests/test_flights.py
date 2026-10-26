import asyncio
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest

from app.flights import (
    FlightOffer, FlightSegment, FlightSearchRequest, ProviderError, attach_utc_schedule_times,
    normalize_response, params_for_search, search_serpapi,
)
from app.models import Airport
from app.settings import Settings


def test_request_maps_one_way_date_currency_class_and_adults_to_provider_params():
    request = FlightSearchRequest(
        origin="DEL", destination="BOM", departure_date=date.today() + timedelta(days=14),
        travel_class="business", currency="inr", adults=3,
    )
    settings = Settings(
        serpapi_key="never-return-this", serpapi_enabled=True, serpapi_monthly_search_limit=1,
        serpapi_daily_search_limit=1, max_external_calls_day=1, max_external_calls_month=1,
        max_flight_searches_per_user_search=1, monthly_external_budget_inr=0,
        serpapi_cost_per_search_inr=0, request_timeout_seconds=5, default_currency="INR",
        default_google_country="in", default_google_language="en", frontend_origins=("http://localhost:3000",),
    )
    params = params_for_search(request, "DEL", "BOM", settings)
    assert params["type"] == 2
    assert params["outbound_date"] == request.departure_date.isoformat()
    assert params["travel_class"] == 3
    assert params["adults"] == 3
    assert params["currency"] == "INR"
    assert "api_key" not in params


def test_normalizer_preserves_missing_price_and_marks_older_provider_results_cached():
    request = FlightSearchRequest(
        origin="DEL", destination="BOM", departure_date=date.today() + timedelta(days=14),
    )
    origin = Airport(id=1, source_id="1", ident="VIDP", type="large_airport", name="Delhi Airport",
                     latitude_deg=0, longitude_deg=0, scheduled_service=True, iata_code="DEL")
    destination = Airport(id=2, source_id="2", ident="VABB", type="large_airport", name="Mumbai Airport",
                          latitude_deg=0, longitude_deg=0, scheduled_service=True, iata_code="BOM")
    retrieved = datetime.now(timezone.utc)
    offers, cached = normalize_response({
        "search_metadata": {"created_at": "2026-10-24 10:00:00 UTC"},
        "best_flights": [{"flights": [
            {"airline": "Example Air", "flight_number": "EX 10", "duration": 60,
             "departure_airport": {"id": "DEL", "name": "Delhi Airport", "time": "2030-01-02 08:00"},
             "arrival_airport": {"id": "BOM", "name": "Mumbai Airport", "time": "2030-01-02 09:00"}},
        ], "total_duration": 60}],
    }, request, origin, destination, retrieved)
    assert cached is True
    assert len(offers) == 1
    assert offers[0].status == "cached"
    assert offers[0].price is None
    assert offers[0].currency == "INR"
    assert offers[0].segments[0].departure_local_time == "2030-01-02 08:00"
    attach_utc_schedule_times(offers, {"DEL": "Asia/Kolkata", "BOM": "Asia/Kolkata"})
    assert offers[0].segments[0].departure_at_utc.isoformat() == "2030-01-02T02:30:00+00:00"
    assert offers[0].segments[0].arrival_at_utc.isoformat() == "2030-01-02T03:30:00+00:00"


def test_timezone_conversion_omits_ambiguous_or_nonexistent_dst_times():
    request = FlightSearchRequest(origin="DEL", destination="BOM", departure_date=date.today() + timedelta(days=14))
    offer = FlightOffer(id="dst", searched_origin="A", searched_destination="B", origin_airport="A", origin_code="NYC",
        destination_airport="B", destination_code="NYC", segments=[FlightSegment(
            departure_code="NYC", arrival_code="NYC", departure_local_time="2027-11-07 01:30",
            arrival_local_time="2027-11-07 02:30")], stops=0, layovers=[], total_duration_minutes=60,
        price=None, currency="INR", airlines=[], booking_url=None, status="live", retrieved_at=datetime.now(timezone.utc))
    attach_utc_schedule_times([offer], {"NYC": "America/New_York"})
    assert offer.segments[0].departure_at_utc is None
    assert offer.segments[0].arrival_at_utc.isoformat() == "2027-11-07T07:30:00+00:00"
    offer.segments[0].departure_local_time = "2027-03-14 02:30"
    attach_utc_schedule_times([offer], {"NYC": "America/New_York"})
    assert offer.segments[0].departure_at_utc is None


def test_http_adapter_uses_secure_provider_key_parameter_and_maps_rate_limits():
    seen = []

    async def successful_handler(request):
        seen.append(request)
        return httpx.Response(200, json={"search_metadata": {"status": "Success"}, "best_flights": []})

    async def rate_limited_handler(_request):
        return httpx.Response(429, json={"error": "Rate limited"})

    async def run():
        payload = await search_serpapi(
            {"engine": "google_flights", "type": 2}, "test-key", 5,
            transport=httpx.MockTransport(successful_handler),
        )
        assert payload["search_metadata"]["status"] == "Success"
        with pytest.raises(ProviderError) as error:
            await search_serpapi(
                {"engine": "google_flights"}, "test-key", 5,
                transport=httpx.MockTransport(rate_limited_handler),
            )
        assert error.value.reason == "provider_rate_limited"

    asyncio.run(run())
    assert seen[0].url.host == "serpapi.com"
    assert seen[0].url.params.get("api_key") == "test-key"
