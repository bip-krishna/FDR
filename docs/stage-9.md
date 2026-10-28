# Stage 9 — Groq AI Layover Explorer

## Implemented foundation

- Added a server-side Groq Chat Completions adapter. Requests happen only through the explicit **Generate layover plan** action after acknowledgement of the safety disclaimer.
- Uses Groq Structured Outputs with a strict JSON Schema and the configured `GROQ_LAYOVER_MODEL` (default `openai/gpt-oss-20b`). Current Groq documentation lists that model as supporting strict structured outputs; API or model errors return an error state without a fallback plan. [Groq Structured Outputs](https://console.groq.com/docs/structured-outputs)
- The model receives only server-sourced candidate records and user interest preferences. Its output schema contains candidate IDs only. The backend generates the explanation and safety warning, so model prose cannot invent place facts, schedules, opening hours, traffic times, or prices.
- Pydantic validates the response. Deterministic validation rejects unknown or repeated IDs, missing explanations, unverified opening/traffic data, user-unverified exit eligibility, baggage re-check uncertainty, closed attractions, and visits that exceed the reserved return window.
- The backend recomputes visit and return times and preserves unknown costs. A plan is never marked as airport-exit authorization.
- Added Groq enable/key/model settings and fail-closed cost accounting. A request requires explicit enablement, credentials, global caps, daily/monthly Groq caps, a per-layover cap, and a configured maximum INR estimate. The reservation is written before the network request and counted even when the provider errors. Defaults remain disabled/zero.
- Added provider status endpoint and an explicit UI action. No automatic calls occur when results load.

## Stage boundary

Stage 9 is **not complete**. Stage 8 has not connected Google Places candidates, opening-hours data, or traffic routes. The public API does not accept candidate facts from the browser and currently returns `verified_candidates_unavailable` before reserving quota or making a Groq call. No real Groq API call was made during implementation. The UI reports that no Groq request occurred.

The deterministic validator currently permits one attraction per plan because no verified inter-attraction travel legs exist. Route-map rendering, real cost/free-tier account verification, and end-to-end generation with live verified candidates remain outstanding. Finish Stage 8 provider wiring, then connect its trusted candidate set to the planner and verify the complete flow before moving to Stage 10.

## Verification

- Backend: 45 tests passed. New tests cover unknown candidate IDs, recomputed timestamps, unknown prices, empty model selections, no-candidate no-call behavior, explicit disclaimer acknowledgement, client-candidate rejection, post-generation validation, strict schema request construction, and per-layover quota reservation.
- Frontend: 16 tests passed; lint, TypeScript, and production build passed.
- No live calls were made. Credentials, provider quotas, and actual per-token prices were not verified.
