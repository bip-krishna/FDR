# Architecture

## Product constraints

FDR compares complete travel journeys from a real origin to a real destination. Search must not pretend provider coverage is exhaustive. Each data element carries provenance and retrieval time where applicable. Unknown fare, schedule, seat, or transfer cost remains unknown.

## Smallest viable shape

Start with a modular monolith:

- **Frontend:** Next.js App Router, TypeScript, React, Tailwind CSS. It owns accessible search input, result presentation, navigation, and user preferences. It never holds flight, AI, or server-side provider secrets.
- **Backend:** FastAPI application with Pydantic request/response schemas and HTTPX provider clients. It is the single boundary for provider calls, validation, rate/cost accounting, and normalized data.
- **Persistence:** SQLite in early development, accessed through SQLAlchemy and migrated with Alembic. Keep models portable; use PostgreSQL for hosted operation where durable storage is required. Add PostGIS only if spatial query needs justify it.
- **Optimization:** provider-neutral itinerary and leg models feed a bounded, time-dependent graph search. Provider payloads do not enter the ranking engine directly.
- **Reference data:** OurAirports CSV is downloaded and indexed as versioned static source data. It is not fetched for each search. Dataset date and source are recorded.
- **Deployment:** frontend and backend may be deployed separately or as a small containerized service after Stage 11 cost and host review. Provider calls stay server-side. Database migrations and persistent storage are required before public deployment.

Avoid Redis, microservices, accounts, and paid fallback services until a demonstrated requirement exists.

## Provider adapter contracts

Adapters should expose typed normalized records and explicit status outcomes rather than leaking upstream JSON:

- `FlightProvider.search(request) -> ProviderResult[list[FlightOffer]]`
- `AirportProvider.search(query) / nearby(point, radius) -> Airport records`
- `RailProvider.search(request) -> ProviderResult[list[TrainOffer]]`
- `RoadRoutingProvider.route(origin, destination, constraints) -> GroundTransfer`
- `PlacesProvider.nearby/search(...) -> Place candidates`
- `WeatherProvider.forecast(point, time_range) -> Forecast`
- `AIItineraryProvider.plan(verified_candidates, constraints) -> validated proposal`

A provider result records provider name, status (live, cached, unavailable, error), retrieval timestamp, optional expiry, and a safe reason. Adapter errors are bounded and do not cause fabricated fallbacks. Each adapter has explicit enablement, timeout, and request limits.

## Initial normalized data

Use timezone-aware timestamps and store instants in UTC. Preserve local timezone identifiers for display. Keep optional upstream fields nullable.

- **Location:** stable ID, display name, city/region/country, coordinates, timezone.
- **Airport:** IATA/ICAO nullable codes, name, coordinates, country, source, type, passenger-service evidence/status. Dataset presence is not proof of scheduled service.
- **Station:** nullable code, name, coordinates, city, source and verification status.
- **FlightOffer:** provider and offer ID, airports, airline/flight numbers, UTC departure/arrival, local timezone IDs, nullable fare/currency/stops/layovers/baggage/booking URL, retrieval time, freshness and fare conditions.
- **TrainOffer:** provider, train and stations, timestamps, class, nullable fare, seat status/quota, official enquiry URL, freshness.
- **GroundTransfer:** endpoints, mode, nullable duration/distance/cost, provider, traffic model, retrieval time.
- **Journey/leg:** ordered legs, known costs and currency, unknown cost components, elapsed/wait time, transfers, connection risks, ranking inputs, provider provenance.
- **LayoverPlan:** airport, arrival/departure, conservative return deadline and usable window, candidate IDs, timings, weather/traffic assumptions, unresolved immigration constraints, warnings and acknowledgement state.

Do not sum currencies without an explicit exchange-rate source and timestamp. Do not treat an unpriced component as free.

## Search and optimization boundaries

The search service first validates the request, then performs bounded airport discovery and shortlist generation before provider calls. `MAX_FLIGHT_SEARCHES_PER_USER_SEARCH` is a hard ceiling, not a target. The first release should prioritize a direct airport pair and a few promising alternatives; expansion is user-triggered. A quota gate runs before every external request.

The graph layer checks chronology, minimum connection buffers, transfer travel time, provider availability, separate-ticket exposure, and known/unknown costs. Ranking offers separate cheapest, fastest, best-overall, and fewest-transfer views. A route with unknown costs cannot be labeled definitively cheapest.

## Security and operations

- Secrets come from server environment or a deployment secret store; never from checked-in files or browser bundles.
- Restrict browser keys to required origins and APIs; keep server credentials separate.
- Use request timeouts, bounded retries only where safe, rate limits, deduplication, and provider-specific usage ledgers.
- Log provider, request class, response status, latency, and estimated cost without logging secrets or unnecessary trip details.
- Expose health and integration readiness separately from travel search.
- No external provider is enabled by default. See `api-integrations.md` and `cost-controls.md`.
