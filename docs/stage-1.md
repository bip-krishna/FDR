# Stage 1 — Frontend foundation

## Implemented

- Responsive Next.js App Router shell with workspace navigation for search, saved journeys, layover exploration, and provider status.
- Search form for city/location, one-way or round-trip dates, passengers, class, nearby airports, rail preference, optional budget, and journey-time limit.
- Field validation for required locations and dates, identical origin/destination, chronological dates, budget, and duration.
- Dedicated results route that carries search criteria forward and presents a truthful empty state while providers are unconfigured.
- Saved, layover, and settings routes clearly identify their future dependencies.
- Yellow, black, white, and neutral design tokens; keyboard focus styles, labels, reduced-motion handling, responsive layout, and a small FDR favicon.

## Checks performed

- `npm run lint` — passed.
- `npm run build` — passed; all routes prerender successfully.
- `npm run test` — passed; 8 validation unit tests.
- Manual browser check: invalid empty search shows field-level errors.
- Manual browser check: valid Delhi-to-Mumbai round trip moves to the results page and reports that no live provider was queried.
- Manual browser check: workspace navigation opens Settings & status; one-way selection removes the return-date field.
- Manual responsive check at 390px viewport width; document width remains 390px with navigation available through horizontal scrolling.
- Browser console: no errors. Next.js scroll behavior warning was resolved.

## Run it

From `frontend/`, run `npm install` once, then `npm run dev`. Open `http://localhost:3000`. Checks: `npm run test`, `npm run lint`, and `npm run build`.

## Limitations

- No location autocomplete, airport lookup, flight/rail provider, map, saved-data persistence, or authentication exists yet.
- Search submission validates and carries criteria to the results page; it does not call an API.
- Results and provider-status pages are structure and honest empty states only. No route, fare, availability, or transfer values are fabricated.
- Form selections are not persisted when navigating away.
- The browser verification environment logged development hot-reload WebSocket reconnect errors after repeated dev-server restarts; normal page and route requests worked, and the production build succeeded.
