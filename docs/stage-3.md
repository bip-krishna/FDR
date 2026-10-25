# Stage 3 — Live flight search

## Implemented

- Added a SerpApi Google Flights provider adapter and `POST /api/flights/search` for future-date, one-way searches. It accepts an IATA airport code or a city/airport name, passenger count, travel class, currency, and an optional nearby-airport search.
- Airport candidates come from the indexed OurAirports data. With nearby search enabled, each city resolves to up to three scheduled-service airports within 250 km of its primary match, ranked by distance. The shortlist puts the primary airport pair first and is bounded by `MAX_FLIGHT_SEARCHES_PER_USER_SEARCH`; it never fans out to every possible pair.
- Added normalization for flight segments, airlines, flight numbers, local airport times, stops, layovers, duration, optional price/currency, Google Flights link, provider status, and retrieval timestamps. Missing price remains null. Provider fares are marked subject to change.
- Added `/api/providers/flight-search` readiness and usage status, a persistent provider-call ledger, request fingerprint hashes, and preflight checks for enablement, credentials, daily/monthly global and SerpApi caps, per-search caps, cost estimate, and monthly budget. Calls are reserved before the network request and retained in the ledger even when the provider errors, conservatively counting attempts.
- Added bounded error handling for provider authentication, rate limits, upstream errors, timeouts, and network failures. Secrets and raw provider errors are not returned to clients.
- Connected the results page to the backend through `NEXT_PUBLIC_FDR_API_URL`. It shows returned provider data, unavailable/blocked/error states, checked and skipped airport pairs, provider timestamps, and a link to the Google Flights result page. It does not claim the link is a guaranteed bookable fare.
- Added configurable CORS origin allowlisting for separate frontend and backend deployments.

## Provider and cost configuration

The local project currently has no SerpApi API key, `ENABLE_SERPAPI` is false, and all search ceilings are zero. The configuration was checked without displaying any secret values. No SerpApi requests were made. To opt in later, add the key to the ignored root `.env`, enable the provider, and set all global/per-search/per-provider limits and the INR cost estimate according to the account plan. Set a zero cost estimate only when the account's included usage has been confirmed; the app cannot detect searches consumed outside its own ledger. Never set a paid search estimate to zero.

As of 2026-10-25, SerpApi documents 250 searches/month on its Free plan and paid plans starting at $25/month; those terms can change. The application does not select a plan or enable paid usage. SerpApi also documents that its Google Flights results can differ from Google Flights in a browser by default. The adapter uses the standard result mode and may use SerpApi's cache; cached status is inferred from provider metadata when available. [Google Flights API](https://serpapi.com/google-flights-api), [current pricing](https://serpapi.com/pricing).

For local frontend/backend communication, copy `frontend/.env.example` to `frontend/.env.local`. For a hosted deployment, set `NEXT_PUBLIC_FDR_API_URL` to the hosted API address when building the frontend and allow the exact frontend origin through `FRONTEND_ORIGINS`. Next.js embeds `NEXT_PUBLIC_` values into browser JavaScript at build time, so changing it later requires a new frontend build. Keep SerpApi credentials only in the backend environment.

## Verification

- Backend unit/API suite — 15 passed. Tests use isolated SQLite and mocked provider transport/responses; they do not make network calls or consume provider quota.
- Missing credentials/disabled provider returns an honest unavailable status without calling upstream.
- A zero request ceiling blocks before network access.
- Nearby airport searches are distance-ranked and stop at the configured pair cap; searched, failed, and skipped airport pairs are reported separately.
- A valid mocked future-date search normalizes a provider response, preserves an unknown fare as null, and records usage.
- Invalid routes and past dates are rejected before provider access.
- Real-index smoke check: the readiness endpoint reported `provider_disabled`; a DEL-to-BOM request returned unavailable with zero provider calls.
- Frontend: 8 tests passed; lint passed; production build passed.
- Test tooling emitted a Starlette/httpx deprecation notice. It did not affect test results.

## Limitations

- No live SerpApi request was possible because credentials are absent and all caps are zero. The provider adapter is verified offline, but live account access, future-date availability, and the account's remaining quota are unverified.
- The initial flow supports one-way searches. Round-trip search remains visible as unsupported and does not call the provider.
- Provider booking tokens are not used to fetch individual booking options. The result links to the matching Google Flights search page; users should confirm fare, baggage, and availability with the seller.
- Provider-local departure and arrival times are retained as returned; they are not converted to UTC because this stage does not add airport timezone resolution.
- The quota ledger is local to the configured database and only counts FDR requests. Configure app-side caps below the account's own remaining allowance; usage outside FDR is not observable.
- Alternative airport pairs are based on source city/name matching, not ground travel time. Ground relevance and transfer comparisons are Stage 4.
- Hosting and production database setup remain in Stage 11.
