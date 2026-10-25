# Stage 5 — End-to-end flight journey optimization

## What is implemented

- Flight offers can be ranked as best overall, lowest known fare, fastest, or fewest flight connections. Nearby airport alternatives remain in the offer set and are ranked together when Stage 3 returned them.
- Users can request airport-access estimates for an individual flight offer. The backend resolves the searched cities, looks up each offered airport's coordinates in OurAirports, resolves airport time zones, and calculates origin-to-airport and airport-to-destination driving legs.
- The estimator includes the configured airport check-in buffer and flight itinerary duration, then returns an estimated door-to-door duration, access distances/times, risks, provider provenance, and retrieval timestamps.
- Offer cards show the known flight fare, explicitly unpriced ground fares, total time only after both ground legs are estimated, provider booking link, and missing-data warnings.
- The ranking avoids comparing a partial flight-only duration as a complete duration against an estimate with both ground legs. Cheapest sorts by known flight fare and labels ground costs as unknown; it does not claim a complete trip cost ranking.
- Each explicit journey estimate is limited to four Google Maps calls: two Geocoding requests and up to two traffic-aware Routes requests. Each call is reserved against global daily/monthly caps, per-SKU caps, cost estimates, and the monthly budget before network access.

## Timing and cost rules

Airport-local provider timestamps are converted with airport coordinates and `timezonefinder`, then `zoneinfo`. If airport coordinates, time-zone data, flight times, or flight duration are missing, the backend returns unavailable without making Maps calls. Current-traffic and future-prediction route results remain labeled separately. The origin route is queried at the configured check-in-buffer lead time. This is a planning estimate; actual check-in needs depend on airline, airport, and itinerary.

No ground transport fare provider is connected, so ground costs always remain unpriced and the known total cost is only the flight fare. No rail leg is added because Stage 6 has not connected a rail source. A Google Routes call is made only after a user requests an estimate and only when all Stage 4 provider switches, credentials, quotas, SKU estimates, global caps, and budget allow it. All Google settings currently default disabled/zero.

## Verification and limits

- Ranking tests cover fare ordering, duration ordering, transfer ordering, incomplete access, and priority for complete door-to-door estimates.
- No live provider requests were made. The configured Google Maps key and quotas are absent, so external estimate behavior remains account-unverified.
- Ground routes are estimated on demand, one flight offer at a time. Flight results remain provisional until the user estimates access for the alternatives being compared.
- Airport check-in buffer defaults to 120 minutes and can be changed with `AIRPORT_CHECKIN_BUFFER_MINUTES`; it is disclosed as a planning assumption.
- Fare comparisons are known-flight-fare comparisons because ground transport costs are unavailable.
