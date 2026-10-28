# Stage 8 — Deterministic Layover Explorer

## Implemented core

- Added `POST /api/layovers/evaluate` and a Layover Explorer screen. Users enter airport-local arrival/departure times with explicit UTC offsets; the backend calculates in UTC and the return deadline is displayed in UTC.
- Detects layovers of at least 10 hours. The default planning window reserves 60 minutes after arrival for terminal transfer and 180 minutes before departure for airport return/security. Both buffers can be adjusted through the API within bounded ranges.
- Returns the latest recommended airport return deadline and conservative available exploration minutes.
- Immigration/airport-exit eligibility defaults to unknown. It is never inferred from layover length. The response always has `airport_exit_authorized: false`; a user-entered verified state is disclosed as user-provided, not independently confirmed.
- Baggage re-check is surfaced as an unmodeled risk. Attraction candidates with unknown eligibility or baggage re-check time are rejected by the deterministic evaluator; candidate evaluation also checks round-trip travel time, visit duration, and supplied opening windows.
- Added a persistent safety disclaimer to the result.

## Provider coverage and remaining work

Stage 8 is **not complete**. The live provider paths required for attraction discovery, opening-hours evidence, traffic-aware route feasibility, and weather are not connected. The result explicitly reports Places, routes, and weather as unavailable and makes no calls. The form currently accepts manually entered flight times instead of automatically extracting connections from flight offers.

Before enabling Google Places, add its own SKU field mask, explicit enable switch, daily/monthly caps, per-request caps, configured cost estimate, and reservation against the shared monthly budget. Google Routes must be called only through the existing reservation-guarded flow. Weather must be fetched only after user action and labeled with source and retrieval time. Until then no attractions are suggested and no layover is represented as feasible for leaving the airport.

## Verification

- Backend: 36 tests passed, including 10-hour threshold, UTC return deadline, unknown exit rejection, conservative travel-window rejection, opening-hours rejection, and API timezone validation.
- Frontend: 16 tests passed; lint, TypeScript, and production build passed.
- No live calls were made. No live attraction, traffic, or weather result was verified.

## Next work within Stage 8

Implement quota-guarded Google Places search with narrowly selected fields and current opening-hours data, Google Routes feasibility for candidate visits, and a user-triggered Open-Meteo forecast path with provenance. Connect detected flight layovers to this screen, keep unresolved immigration eligibility unverified, and add tests for provider failure, quota blocks, stale forecasts, and candidate feasibility before advancing to Stage 9.
