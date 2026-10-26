# Stage 7 — Multimodal graph optimization

## Implemented

- Added a bounded, time-dependent route graph in `backend/app/multimodal.py`. It finds chronological paths over flight, train, and ground edges, rejects repeated-node loops and missed connection buffers, and caps each request at 120 edges, 8 segments per route, 100 requested routes, and 25,000 search states.
- Added airport-local-to-UTC conversion to flight offers using airport coordinates from OurAirports and IANA time zones. Ambiguous or nonexistent daylight-saving timestamps remain unset, so the frontend will not use them to claim a feasible route.
- Added `/api/journeys/optimize`. The results page calls it only after the user asks to evaluate the flight offers whose two airport-access legs they have estimated. The optimizer makes no provider calls.
- Added transfer buffers: train-to-flight 180 minutes, flight-to-train 90, separate flight-to-flight 120, train-to-train 45, ground-to-flight 120, flight-to-ground 30, train-to-ground 30, ground-to-train 45, and ground-to-ground 15. Connections on the same known flight ticket group use a smaller internal connection buffer.
- Added fare completeness rules. A comparable total fare is returned only when every segment has a known fare in the same currency. Partial known fares are identified separately; currency conversion is not guessed. Pareto dominance compares only complete fares in matching currencies; unknown-cost routes remain incomparable.
- Routes carry provider/freshness data, separate-ticket and mode-change risks, provider links where supplied, and `confirmed_bookable: false`. Cached/static timetables are labeled for reconfirmation.
- Added the Stage 7 route panel to journey results. It shows candidate segments, duration, known or complete fare status, Pareto status, risks, and available provider links. A requested rail search links to Stage 6's official enquiry page because no in-app railway schedule feed is connected.

## Timing and estimation notes

Flight connection chronology is compared as UTC instants. Flight itinerary offers are represented as one edge each so an offer's aggregate fare is not incorrectly allocated across separately recombined legs. Ground access is represented as separate origin and destination edges. To leave the configured airport-arrival buffer before a flight and a short exit buffer after landing, the route graph shifts the ground segment's planning times; it discloses when those planning times differ from the departure time used for the Google traffic estimate. These are estimates, not guaranteed connection times.

The graph can evaluate train and rail-only edges supplied by a permitted provider, but Stage 6 has no such schedule feed. It currently does not invent train edges or create station-to-airport transfer estimates. Ground transfer fares also remain unavailable, so a full trip fare is unknown for routes that include ground legs.

## Verification

- Backend: 31 tests passed, including UTC conversion, DST ambiguity, chronology, connection buffers, mixed-mode fixture paths, Pareto comparisons, currency handling, unknown fares, and API validation.
- Frontend: 16 tests passed; lint and TypeScript checks passed; the production build completed.
- Route fixtures exist only in isolated tests. No fixture schedules are displayed as production results. No Google Maps, flight, or rail provider calls are made by the optimizer itself.

## Manual verification

Configure the flight and Maps providers as described in their stage notes. Run a one-way search, estimate airport access for the flight offers you want to compare, then select **Evaluate connections**. The panel only receives offers with UTC-resolved schedules and both ready ground legs. If its buffers rule out every path, it displays no feasible route instead of relaxing them.

## Remaining limitations

- Live train routes, fares, and seat availability remain unavailable pending an authorized provider; the optimizer cannot include train legs until one is connected.
- Flight results and Google Maps access estimates require their own credentials and configured request/cost limits. They remain disabled by default.
- Ground costs are missing, so airport-access routes cannot claim a complete trip-cost Pareto ranking.
- Connections between different airports/stations require an explicit ground edge. The route graph supports one, but the current results flow only creates access edges at the journey's outer origin and destination.
