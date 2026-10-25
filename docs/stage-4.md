# Stage 4 — Ground transfers

## What is implemented

- `GET /api/providers/google-maps` reports non-secret setup status and configured ceilings.
- `POST /api/transfers/estimate` geocodes two entered locations and requests a Google Routes driving route. Inputs support cities, airports, and railway stations.
- Traffic-aware duration, static duration, route distance, encoded route geometry, retrieval time, and departure mode are returned separately.
- The results page includes a deliberate route request panel. It draws the returned route geometry in the existing yellow, charcoal, and white visual system and labels current traffic versus a future prediction.
- Each external request is reserved in the shared usage ledger before network access. Global daily/monthly call ceilings and monthly INR budget apply alongside separate daily/monthly geocoding and Routes ceilings, estimated INR per-call costs, and a maximum of three provider calls per transfer.
- The route geometry is rendered as local SVG; there are no map tile or browser key requests.

## Provider and cost controls

All Google Maps switches, SKU quotas, and the per-transfer cap default to disabled/zero. A route estimate needs two Geocoding SKU requests and one Routes Compute Routes Pro SKU request. Google classifies `TRAFFIC_AWARE` as Routes Pro. Costs remain unset in `.env.example`; configure the account's applicable current India or global tier and an INR estimate. A missing estimate, key, switch, global cap, provider cap, per-transfer cap, or budget blocks before the relevant request. Google billing alerts are not a hard spend cap, so the application enforces its own ceilings too.

No API key or quota configuration is present in the local environment, so the API currently returns unavailable and makes no Google request. Route Matrix is not used because the interactive panel calculates one explicit pair at a time; Matrix elements would add fan-out and a different billing unit without benefit here.

## Stage boundary

This stage returns a ground-leg duration that a journey optimizer can consume. The panel displays a requested ground leg independently; combining city access with flight candidates and changing their full-journey rank belongs to Stage 5, where the full itinerary model is introduced.
