# PROJECT MASTER SPECIFICATION
# Build a Real-Time Multimodal Travel Planning Platform

You are Codex, acting as a senior full-stack engineer, systems architect, UI/UX designer, and integration engineer.

Your assignment is to build a real, functional, personally usable travel-planning platform from scratch.

This is initially a student-built project intended for practical personal use, technical demonstration, and potential college funding. However, its architecture should support future commercialization.

Do not build a fake showcase website, static mockup, landing page, or nonfunctional prototype.

The goal is a working application that uses real APIs and real travel information wherever authorized sources are accessible.

Build the application incrementally in controlled, verifiable stages.

**IMPORTANT: Do not attempt the entire project in one execution. Implement only one stage at a time. Stop after completing and verifying each stage. Ask me to reply "Continue to Stage N" before proceeding.**

---

# 1. PRODUCT VISION

The application is a smart, multimodal, door-to-door travel comparison and planning platform.

Conventional flight comparison websites primarily compare flights between specified airports.

Our platform must expand the search space to include:

- Flights from nearby alternative airports.
- Flights arriving at nearby alternative destination airports.
- Ground transport to and from airports.
- Indian Railways connections.
- Train + flight journeys.
- Flight + train journeys.
- Ground transfers between airports and stations.
- Multiple feasible combinations of transport modes.
- Optional sightseeing during long airport layovers.

The user should be able to search using cities or actual locations rather than being forced to select airport codes.

The platform should calculate:

1. Total estimated journey cost.
2. Total estimated travel duration.
3. Connection feasibility.
4. Transfer costs.
5. Waiting times.
6. Available booking options.
7. Journey risks.
8. Alternative routes worth considering.

Rank results by:

- Cheapest.
- Fastest.
- Best overall.
- Fewest connections.

Do not claim to search every possible fare unless provider coverage actually supports that claim.

The application should clearly explain why one itinerary is recommended over another.

---

# 2. REAL-DATA REQUIREMENTS

This requirement is non-negotiable.

I do not want a project that depends on simulated flight prices, fabricated train-seat availability, or hardcoded travel results.

Use real, current production information from accessible providers.

Important distinctions:

- Live: fetched from an actual production service.
- Cached: fetched previously; display the retrieval timestamp.
- Estimated: calculated from actual data but not guaranteed.
- Static reference data: airport/station geographic databases.
- Unavailable: information that could not be retrieved.

Every itinerary and travel-data element must indicate its data provenance.

Never display simulated values as live data.

If a provider cannot be used because of account restrictions, legal restrictions, quotas, or absent credentials:

1. Keep the integration interface implemented.
2. Show an accurate integration status.
3. Explain which credentials or permissions are missing.
4. Allow the rest of the application to function.
5. Never silently substitute fabricated results.

Fixture data may be used exclusively for isolated automated tests, explicitly labeled as fixtures.

The goal is the maximum practical functionality possible with free tiers and legitimate API access.

I am willing to configure billing methods for providers offering recurring free allowances.

However, I want API usage costs to remain ₹0 wherever practical.

No application feature may intentionally consume billable quota beyond configured limits.

Do not purchase subscriptions, upgrade plans, or enable paid services without my explicit permission.

---

# 3. TECH STACK

Use the following preferred technology stack.

## Frontend

- Next.js with App Router.
- TypeScript.
- React.
- Tailwind CSS.
- Lucide icons.
- TanStack Query where appropriate.
- Accessible, responsive UI components.

## Backend

- Python.
- FastAPI.
- Pydantic.
- HTTPX for external requests.
- SQLAlchemy.
- Alembic for migrations.
- NetworkX for initial graph algorithms.
- Redis only when justified; avoid unnecessary deployment complexity.

## Database

Use SQLite for the initial local development stages.

Design the models so PostgreSQL with PostGIS can be introduced later.

## Mapping

- Google Maps Platform.
- Google Routes API.
- Google Places API.
- Google Geocoding / Place Autocomplete as appropriate.

## Flight Information

Primary:
- SerpApi Google Flights API.

Optional secondary:
- Amadeus Production APIs if accessible under a suitable free allowance.

Design a modular provider interface to allow additional suppliers later.

## Airport Dataset

- OurAirports.

## Railway Information

- Authorized Indian Railways / IRCTC-linked data providers where available.
- Permitted public datasets for schedules and geographic reference data.
- Official railway enquiry links where automated availability cannot legally be obtained.

## AI

- GroqCloud API.

## Weather

- Open-Meteo API.

## Testing

- Pytest.
- Vitest where useful.
- Playwright for end-to-end browser tests.

## Development

- Git.
- Environment-variable configuration.
- Docker Compose, if necessary.
- Clear local run scripts.
- README documentation.

Favor a simple, maintainable architecture over unnecessary microservices.

---

# 4. COMPLETE API DOCUMENTATION AND REFERENCE LINKS

Read the relevant official documentation before implementing each integration.

## A. Flight Search — SerpApi

Documentation:
https://serpapi.com/google-flights-api

Pricing:
https://serpapi.com/pricing

API dashboard:
https://serpapi.com/dashboard

Use for:

- Current flight search results.
- Flight prices.
- Airlines.
- Departure and arrival times.
- Layover durations.
- Available itinerary details.
- Booking or deep links when returned.

Respect monthly request allowances.

Check provider terms and limitations.

Do not assume all returned prices are final bookable fares.

## B. Amadeus

Developer portal:
https://developers.amadeus.com/

API catalog:
https://developers.amadeus.com/self-service

Developer guides:
https://developers.amadeus.com/self-service/apis-docs/guides

Use production data only when production access has been correctly configured.

Do not present sandbox data as real current fares.

Amadeus is optional, not a dependency blocking development.

## C. Google Maps Platform

Developer portal:
https://developers.google.com/maps

Google Cloud Console:
https://console.cloud.google.com/

India pricing:
https://developers.google.com/maps/billing-and-pricing/pricing-india

Pricing details:
https://developers.google.com/maps/billing-and-pricing/india

Routes API:
https://developers.google.com/maps/documentation/routes

Compute Routes:
https://developers.google.com/maps/documentation/routes/compute_route_directions

Route Matrix:
https://developers.google.com/maps/documentation/routes/compute_route_matrix

Traffic preferences:
https://developers.google.com/maps/documentation/routes/config_trade_offs

Traffic models:
https://developers.google.com/maps/documentation/routes/traffic-model

Places API:
https://developers.google.com/maps/documentation/places/web-service/overview

Maps JavaScript API:
https://developers.google.com/maps/documentation/javascript

Geocoding:
https://developers.google.com/maps/documentation/geocoding

API security:
https://developers.google.com/maps/api-security-best-practices

Billing budgets:
https://cloud.google.com/billing/docs/how-to/budgets

Quotas:
https://cloud.google.com/docs/quotas

Use for:

- Origin and destination discovery.
- Airport access routes.
- Station-to-airport transfers.
- Ground journey durations.
- Traffic-aware ETAs.
- Route distance calculations.
- Nearby attractions.
- Restaurant discovery.
- Attraction opening hours.
- Visual journey mapping.
- Layover return-time planning.

Use the correct billing SKU for each API request.

Prefer requests with minimal necessary response fields.

Only use traffic-aware optimal routing when the extra cost and accuracy are justified.

Use realistic traffic estimates, never guarantees.

## D. OurAirports

Dataset:
https://ourairports.com/data/

GitHub:
https://github.com/davidmegginson/ourairports-data

Use for:

- Airport names.
- IATA and ICAO codes.
- Coordinates.
- Airport types.
- Geographic discovery.

Download the dataset locally and index it.

Do not request the entire dataset from the network on every user search.

Remember that the presence of an airport in the dataset does not guarantee scheduled passenger service.

## E. Indian Railways

Official IRCTC:
https://www.irctc.co.in/

Indian Railways enquiry:
https://enquiry.indianrail.gov.in/

National Train Enquiry System:
https://enquiry.indianrail.gov.in/ntes/

Indian Railways seat availability:
https://indianrail.gov.in/enquiry/SEAT/SeatAvailability.html

Research authorized access to:

- Train schedules.
- Train numbers.
- Railway stations.
- Seat availability.
- Fare classes.
- Reservation quotas.
- RAC and waiting-list statuses.

Do not rely on unofficial scraping or unsupported reverse-engineered endpoints.

Do not bypass CAPTCHAs or access controls.

If no authorized programmatic data source is available, integrate official external enquiry links and clearly mark seat status as unavailable inside our app.

Build a TrainProvider abstraction so an authorized service can be connected later.

## F. Groq API

Console:
https://console.groq.com/

Documentation:
https://console.groq.com/docs

API reference:
https://console.groq.com/docs/api-reference

Structured outputs:
https://console.groq.com/docs/structured-outputs

Rate limits:
https://console.groq.com/docs/rate-limits

Use for:

- Layover sightseeing plans.
- Personalized recommendations.
- Natural language itinerary summaries.
- Explanations of route choices.

Never depend on an LLM for time-critical calculations.

Use supported structured outputs and validate every response.

## G. Open-Meteo

Documentation:
https://open-meteo.com/en/docs

Use for:

- Weather forecasts.
- Rain probability.
- Temperature.
- Weather-related sightseeing warnings.

Respect non-commercial free-use conditions and API limits.

## H. Optional Mapping Fallback

Geoapify:
https://www.geoapify.com/

Documentation:
https://apidocs.geoapify.com/

Use only when justified as a fallback or alternative to Google.

---

# 5. DESIGN SYSTEM — STRICT REQUIREMENTS

The application's visual identity is:

**YELLOW + BLACK + WHITE.**

No generic AI-generated visual styling.

No gradients.

No glassmorphism.

No glowing effects.

No random purple, blue or cyan decorative accents.

No excessive shadows.

No unnecessary floating cards.

No decorative AI illustrations.

No fake dashboard graphs that do not show meaningful data.

Use a crisp, minimal, functional product design.

Suggested palette:

- Primary yellow: #FACC15.
- Primary black: #111111.
- Secondary black: #1C1C1C.
- White: #FFFFFF.
- Off-white: #F7F7F5.
- Muted gray: #737373.
- Border: #E5E5E5.

Use restrained semantic colors only when necessary for warnings, errors, and statuses.

Design characteristics:

- High contrast.
- Strong typography.
- Clear hierarchy.
- Generous but controlled spacing.
- Sharp and slightly rounded corners.
- Flat buttons.
- Thin borders.
- Compact travel result cards.
- Minimal animations.
- Information density suitable for travel comparison.
- Responsive mobile experience.

Avoid blindly copying Skyscanner or Google Flights.

Make the interface feel like a purpose-built transport intelligence product.

Core pages:

1. Search page.
2. Flight and multimodal results.
3. Route details.
4. Map-based journey visualization.
5. Layover Explorer.
6. Saved journeys.
7. Settings and API usage dashboard.

Include:

- Light theme as the default.
- Optional black-based dark theme.
- Consistent yellow accents in both themes.

Do not make every screen bright yellow.

---

# 6. APPLICATION ARCHITECTURE

Use a modular architecture.

Suggested repository structure:

```text
travel-planner/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── hooks/
│   ├── lib/
│   └── styles/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── providers/
│   │   │   ├── flights/
│   │   │   ├── rail/
│   │   │   ├── maps/
│   │   │   ├── weather/
│   │   │   └── ai/
│   │   ├── services/
│   │   ├── optimization/
│   │   └── database/
│   └── tests/
├── data/
├── docs/
├── scripts/
├── .env.example
├── .gitignore
└── README.md
```

Use provider adapters.

Each external data provider should have:

- A well-defined interface.
- Configuration validation.
- Normalized response schemas.
- Timeouts.
- Rate limiting.
- Error handling.
- Provider-specific data provenance.
- Cost/usage accounting.
- Clear unavailable-data behavior.

Examples:

FlightProvider
AirportProvider
RailProvider
RoadRoutingProvider
PlacesProvider
WeatherProvider
AIItineraryProvider

The optimization engine must depend on normalized data interfaces, not directly on provider-specific JSON.

---

# 7. DATA MODEL

Design normalized models for:

## Location

- ID.
- Name.
- City.
- Region.
- Country.
- Latitude.
- Longitude.
- Time zone.

## Airport

- IATA code.
- ICAO code.
- Name.
- Coordinates.
- Country.
- Passenger service eligibility, where verifiable.

## Railway Station

- Station code.
- Name.
- Coordinates.
- City.
- Available metadata.

## Flight Offer

- Provider.
- Provider offer identifier.
- Origin airport.
- Destination airport.
- Airline.
- Flight numbers.
- Departure timestamp.
- Arrival timestamp.
- Time zones.
- Price.
- Currency.
- Stops.
- Layover details.
- Baggage information when available.
- Booking URL when available.
- Retrieved timestamp.
- Data freshness.
- Fare conditions when available.

## Train Offer

- Provider.
- Train number.
- Origin.
- Destination.
- Departure.
- Arrival.
- Travel class.
- Fare.
- Seat-availability status.
- Quota.
- Data freshness.

Missing fields must remain null rather than fabricated.

## Ground Transfer

- Origin.
- Destination.
- Travel mode.
- Duration.
- Distance.
- Estimated cost.
- Traffic model.
- Retrieval timestamp.

## Journey

- Ordered travel legs.
- Total monetary cost.
- Currency.
- Total duration.
- Waiting duration.
- Connection count.
- Transfer count.
- Risk level.
- Ranking metrics.
- Missing-data indicators.

## Layover Plan

- Airport.
- Arrival time.
- Departure time.
- Latest safe return time.
- Available exploration duration.
- Suggested attractions.
- Visit order.
- Travel durations.
- Visit durations.
- Weather.
- Traffic assumptions.
- Safety warnings.
- Disclaimer acceptance.

All timestamps must be timezone-aware.

Store canonical timestamps in UTC while displaying local time with the correct timezone.

---

# 8. CORE JOURNEY SEARCH REQUIREMENTS

The user should enter:

- Origin city or location.
- Destination city or location.
- Departure date.
- Optional return date.
- Passenger count.
- Preferred travel class.
- Maximum budget.
- Maximum journey duration.
- Preferred modes.
- Willingness to use alternative airports.
- Maximum acceptable airport access distance or time.

Search behavior:

1. Geocode origin and destination.
2. Discover nearby relevant airports.
3. Discover railway stations when supported.
4. Estimate access times.
5. Filter unrealistic transport hubs.
6. Generate possible airport pairs.
7. Query promising flight routes.
8. Retrieve permitted railway options.
9. Generate multimodal candidate journeys.
10. Validate all transfers and time constraints.
11. Calculate end-to-end costs.
12. Rank feasible journeys.
13. Display detailed comparisons.

Important:

A ₹3,000 flight is not automatically cheaper than a ₹4,000 flight if reaching its departure airport costs ₹1,500.

Include both origin-side and destination-side ground costs.

Avoid constructing an enormous number of API calls.

Use a shortlist strategy and allow the user to expand the search manually.

Display incomplete coverage when only a subset of airport combinations was checked.

---

# 9. ROUTE OPTIMIZATION REQUIREMENTS

Model the transportation network as a time-dependent graph.

Nodes can represent:

- Airports.
- Stations.
- Transfer points.
- Origin and destination locations.

Edges represent:

- Flights.
- Trains.
- Road transfers.
- Walking links where suitable.
- Waiting or transfer operations.

Each edge should carry:

- Departure and arrival times.
- Cost.
- Duration.
- Transport type.
- Provider.
- Availability.
- Reliability or risk metadata.

Requirements:

- No time-travel connections.
- No impossible train-to-flight transfers.
- No negative travel time.
- No double-counted costs.
- No missed connection hidden as valid.
- Separate-ticket risk must be disclosed.
- Costs must be normalized into a common currency if comparison requires it.
- Missing ground fares must not silently become zero-cost transfers.

Implement a practical time-dependent path search with pruning and multi-criteria ranking.

Use Pareto filtering when useful.

Do not rely on a simple weighted sum alone if that eliminates meaningful alternatives.

The user should see multiple useful choices rather than only one theoretically optimal path.

Add configurable connection buffers.

Distinguish protected airline connections from self-transfers.

---

# 10. LAYOVER EXPLORER

This is one of our differentiating product features.

The user may have a long airport layover during a journey.

When the layover exceeds 10 hours, the interface may offer:

"Explore this city during your layover."

The button must be optional.

Do not automatically invoke Groq when search results appear.

Shorter layovers may be eligible for nearby-airport activities only if a separate feasibility policy explicitly allows them.

Never recommend exploration solely because a destination is geographically close.

The system must consider:

- Immigration rules.
- Visa and transit permissions.
- Airport exit eligibility.
- Baggage and check-in requirements.
- Terminal transfers.
- Flight arrival and departure times.
- Airport return requirements.
- Ground transport.
- Traffic.
- Security buffers.
- Attraction opening hours.
- Weather.
- User budget.
- Physical feasibility of the itinerary.

Unknown visa or exit eligibility must be treated as unverified, not approved.

Do not present international airport-exit eligibility as confirmed without an appropriate authoritative source.

## Layover user flow

1. User sees an eligible long layover.
2. User clicks "Explore Layover".
3. Application gathers preferences.
4. Application verifies available travel-time information.
5. It calculates a conservative usable time window.
6. It identifies nearby candidate attractions.
7. It obtains route durations and traffic estimates.
8. It obtains weather information.
9. It calls Groq with verified structured context.
10. Groq proposes an itinerary.
11. Backend validates the proposed itinerary.
12. Invalid activities are removed or the plan is rejected.
13. Final route is displayed on a map.
14. User sees the latest recommended airport return deadline.
15. User sees and acknowledges a disclaimer.

## Groq restrictions

Groq must not invent:

- Opening hours.
- Distances.
- Traffic data.
- Airport procedures.
- Visa permissions.
- Flight schedules.
- Ticket prices.

Groq must select or organize candidate places obtained from real providers.

Generate a JSON itinerary containing:

- Candidate attraction IDs.
- Visit sequence.
- Proposed times.
- Activity descriptions.
- Estimated costs where supported.
- Warnings.

Validate using Pydantic.

Use a deterministic backend validator.

If the plan fails validation, return a clear reason and offer a shorter itinerary.

Never allow Groq to override a safety constraint.

## Example disclaimer

"Suggested layover activities are estimates and not guarantees. Traffic, immigration, airport security, flight schedules, and local conditions may change. Confirm that you are allowed to leave and re-enter the airport. Verify your boarding requirements and return early enough for your onward journey. The platform cannot guarantee that a connection will be made."

Require acknowledgement before presenting a trip as suitable for leaving the airport.

---

# 11. API COST CONTROL

Extremely important.

This is a personal-use student project.

The intended API expenditure is ₹0.

A billing account may be configured to access free usage tiers.

However, the application must not assume billing alerts guarantee zero charges.

Implement:

- Per-provider request counters.
- Per-provider daily limits.
- Per-provider monthly limits.
- Cost estimation based on configured SKU rates.
- Global API-call budget.
- Rate limiting.
- Caching consistent with provider terms.
- Duplicate request suppression.
- API timeouts.
- Automatic refusal of searches exceeding remaining quota.
- A usage dashboard.
- Request cost logging where known.
- Optional disable switches for expensive services.

Searches involving many airport combinations must not cause uncontrolled request multiplication.

Expose environment settings such as:

```env
SERPAPI_API_KEY=
GOOGLE_MAPS_API_KEY=
GROQ_API_KEY=
AMADEUS_CLIENT_ID=
AMADEUS_CLIENT_SECRET=

ENABLE_AMADEUS=false
ENABLE_RAIL_PROVIDER=false
ENABLE_TRAFFIC_AWARE_ROUTES=true
ENABLE_GROQ_LAYOVER=true

MAX_FLIGHT_SEARCHES_PER_USER_SEARCH=4
MAX_PLACES_LOOKUPS_PER_LAYOVER=10
MAX_GROQ_CALLS_PER_LAYOVER=1

MONTHLY_EXTERNAL_API_BUDGET_INR=0
```

These are examples. Implement a realistic quota model rather than assuming request count alone equals monetary cost.

Do not store secrets in Git.

Use server-side credentials where appropriate.

Use restricted browser keys only for services that require browser access.

Never expose flight-provider or Groq secrets in client-side bundles.

Do not automatically enable paid fallback providers.

---

# 12. STAGED IMPLEMENTATION PLAN

Build sequentially.

Every stage must include:

- Actual implementation.
- Automated tests.
- Manual verification instructions.
- Screenshots where useful.
- Documentation updates.
- Known limitations.
- Working and nonworking features.
- Relevant Git commit, if the environment supports Git.

Do not declare a stage finished simply because code compiles.

Run tests and fix detected failures before completion.

Stop after each stage and request permission to proceed.

## STAGE 0 — Technical feasibility and project foundation

Tasks:

1. Inspect the current workspace.
2. Determine whether a repository already exists.
3. Verify local versions of Node.js and Python.
4. Review official API documentation.
5. Document which integrations require credentials, billing, or approval.
6. Identify the smallest viable production-data architecture.
7. Define provider interfaces and normalized schemas.
8. Establish API cost-control strategy.
9. Create a development roadmap.
10. Initialize Git if appropriate.

Deliverables:

- README.md.
- docs/architecture.md.
- docs/api-integrations.md.
- docs/cost-controls.md.
- docs/roadmap.md.
- .env.example.
- Initial repository structure.

Acceptance criteria:

- No unverified claims of provider availability.
- No fake data dependencies.
- Clear development setup.
- Clear architecture.
- Clear credential requirements.

STOP after Stage 0.

## STAGE 1 — Frontend foundation

Build the actual application shell.

Features:

- Responsive app layout.
- Yellow-black-white design system.
- Search form.
- Origin and destination fields.
- Date selection.
- Passenger selection.
- Travel preferences.
- Nearby airport toggle.
- Results page structure.
- Loading, error, and empty states.

Do not create fake results to make the page appear populated.

Use proper frontend state and validation.

Acceptance criteria:

- Frontend runs locally.
- Navigation works.
- Forms validate correctly.
- Responsive design works.
- No gradients or unwanted colors.
- No simulated fares shown.

STOP after Stage 1.

## STAGE 2 — Airport database and location discovery

Download and process OurAirports.

Create searchable airport records.

Implement:

- Airport search.
- City search.
- IATA lookup.
- Distance calculations.
- Nearby airport discovery.
- Airport ranking.
- Airport eligibility filters.
- Ground-travel relevance filters when routing is accessible.

Expose backend APIs for airport lookup.

Tests should include:

- Known airport code lookup.
- Nearby airport ranking.
- Missing IATA codes.
- Airports without commercial passenger service.
- Invalid geographic input.

Acceptance criteria:

- Searching a real city returns relevant nearby airports.
- Results use actual airport database records.
- No hardcoded airport lists.
- Output includes coordinates and codes.

STOP after Stage 2.

## STAGE 3 — Live flight search

Integrate SerpApi Google Flights using production searches.

Implement:

- Provider authentication.
- One-way searches.
- Date selection.
- Flight normalization.
- Price and currency.
- Airline details.
- Stops and layovers.
- Provider booking links.
- Retrieval timestamps.
- Error handling.
- Quota tracking.

Then build nearby-airport combination search with a request budget.

Do not automatically query every pair.

Handle:

- No flights available.
- Missing provider key.
- API rate limits.
- Expired quota.
- Invalid airport pairs.
- Missing price data.
- Provider service failures.

Compare retrieved flight prices against the corresponding source when possible.

Acceptance criteria:

- Actual future-date flight searches can be performed.
- Live provider results appear.
- Prices retain provenance and timestamps.
- Searches remain within the configured request budget.
- No silent fallback to fixtures.

STOP after Stage 3.

## STAGE 4 — Google Maps and traffic-aware transfers

Integrate:

- Geocoding.
- Routes.
- Route Matrix where justified.
- Map visualization.
- Traffic-aware route estimates.

Create:

- City-to-airport transfer.
- Airport-to-destination transfer.
- Railway-station-to-airport transfer.
- Transfer distance.
- Transfer duration.
- Congestion-aware estimates.
- Traffic-aware arrival calculations.

Only enable billable functionality under safe, explicitly configured quotas.

Handle unavailable traffic results transparently.

Acceptance criteria:

- Actual route geometries are displayed.
- Ground access time affects ranking.
- Long-distance transfers are not treated as free or instantaneous.
- Current-traffic estimates are distinguished from future predictions.

STOP after Stage 4.

## STAGE 5 — End-to-end flight journey optimization

Combine Stages 2–4.

For each flight candidate, calculate:

Origin → departure airport → flight itinerary → arrival airport → destination.

Build ranking logic for:

- Cheapest.
- Fastest.
- Best overall.
- Fewest transfers.

Display:

- Detailed route.
- Flight price.
- Ground cost estimates, if sourced.
- Total known cost.
- Unpriced components.
- Total journey duration.
- Risks.
- Source and retrieval time.
- Booking link.

Do not rank unknown-cost itineraries as definitively cheaper than fully priced journeys.

Acceptance criteria:

- Nearby airport alternatives are considered.
- Door-to-door calculations work.
- Travel time includes airport transfers.
- Incomplete fare coverage is disclosed.
- Algorithms are unit tested.

STOP after Stage 5.

## STAGE 6 — Indian Railways integration

Build rail provider architecture.

Implement:

- Station discovery.
- Railway segment normalization.
- Schedule integration where a permitted source exists.
- Travel class representation.
- Live fare and seat availability only when authorized.
- Official enquiry links as fallback.
- Railway-specific data freshness.

Research and document actual API accessibility.

Never invent availability.

Acceptance criteria:

- Supported train routes integrate into the travel model.
- Unsupported live seat information is clearly marked unavailable.
- Users can access official availability enquiries.
- The feature operates without an unauthorized scraping dependency.

STOP after Stage 6.

## STAGE 7 — Multimodal graph optimization

Combine flights, trains and ground transfers.

Support:

- Train → flight.
- Flight → train.
- Flight → ground transfer → flight where useful.
- Airport alternatives on both ends.
- Rail-only journeys when supported.
- Ground-only alternatives when useful.

Implement:

- Time-dependent graph construction.
- Feasibility checks.
- Transfer buffers.
- Ranking.
- Risk explanations.
- Pareto filtering.

Prevent impossible connections.

Acceptance criteria:

- Route engine can evaluate mixed-mode journeys.
- Arrival/departure chronology is correct.
- Total cost and duration calculations are correct.
- Separate-ticket warnings appear where appropriate.
- No unsupported journey is presented as confirmed bookable.

STOP after Stage 7.

## STAGE 8 — Layover Explorer without AI

First implement the deterministic logic.

Detect layovers.

Default threshold: 10 hours.

Implement:

- Eligibility state.
- Airport exit warnings.
- Available exploration time.
- Return-to-airport buffer.
- Attraction discovery using Google Places.
- Opening-hours checks.
- Traffic-aware route feasibility.
- Weather lookup.
- Latest recommended airport return deadline.

Do not use Groq yet.

Acceptance criteria:

- Long layovers can be detected.
- Feasible attraction candidates can be identified.
- Unsafe plans are rejected.
- Missing immigration information is acknowledged.
- The backend does not treat a long layover as automatic exit permission.

STOP after Stage 8.

## STAGE 9 — Groq AI Layover Explorer

Integrate Groq.

Only call Groq after explicit user action.

The model receives verified candidates and constraints.

Implement:

- User interest preferences.
- Structured JSON generation.
- Strict schema validation when supported.
- Post-generation itinerary validation.
- Route map.
- Estimated exploration costs.
- Explanation of selected attractions.
- Disclaimers.
- Error and unavailable states.

Acceptance criteria:

- Groq generates plans based on actual supplied places.
- Generated plans are verified by backend logic.
- Invalid itineraries are rejected.
- Safety buffers remain intact.
- No invented attractions or opening hours appear.

STOP after Stage 9.

## STAGE 10 — Personal-use improvements

Implement:

- Saved searches.
- Favorite routes.
- Search history.
- Provider usage dashboard.
- Fare retrieval timestamps.
- Search caching.
- Manual refresh.
- Booking redirects.
- Weather warnings.
- Better mobile experience.
- Dark theme.
- Improved error states.
- Provider health dashboard.

Add user authentication only if truly necessary.

For a personal local application, avoid unnecessary external authentication dependencies.

Acceptance criteria:

- Application is convenient for repeated personal use.
- Quota counters operate correctly.
- No hidden repeated API requests.
- Saved data persists.
- App remains functional after restart.

STOP after Stage 10.

## STAGE 11 — Comprehensive testing and deployment

Perform:

- Unit testing.
- Integration testing.
- Browser-based end-to-end testing.
- Responsive testing.
- API failure testing.
- API quota exhaustion testing.
- Security checks.
- Data freshness checks.
- Accessibility checks.
- Timezone checks.
- Edge-case connection testing.

Prepare deployment configuration.

Prefer the least expensive deployment suitable for personal use.

Do not purchase hosting or activate billable resources.

Document environment setup.

Acceptance criteria:

- All critical flows tested.
- No exposed secrets.
- Real provider integrations verified where credentials are supplied.
- All limitations documented.
- Application can be operated locally without paid hosting.

STOP after Stage 11.

## STAGE 12 — College funding and demonstration preparation

Prepare a professional technical showcase.

Include:

- Project overview.
- Problem definition.
- Existing travel search limitations.
- Technical architecture.
- Real integrations.
- Route optimization explanation.
- Layover Explorer explanation.
- API costs and constraints.
- Data coverage limitations.
- Real case studies.
- Comparison methodology.
- Known risks.
- Product roadmap.
- Funding requirements.

Create reproducible case studies using actual provider data when available.

Compare:

- Direct-airport search.
- Alternative airport search.
- End-to-end optimization.
- Multimodal travel where supported.

Do not fabricate savings.

Document sample dates, search timestamps, and coverage limitations.

Acceptance criteria:

- Demonstration is reproducible.
- Clear distinction between functional features and planned integrations.
- Funding request is based on identifiable technical needs.
- Project is credible as a foundation for future commercialization.

STOP after Stage 12.

---

# 13. TESTING PRINCIPLES

For every stage:

- Run actual commands.
- Verify installation.
- Validate API contracts.
- Execute tests.
- Inspect frontend behavior.
- Fix failures.
- Update README.
- Report unresolved issues.

Use mocks or fixtures inside isolated tests only.

Do not pass fixtures off as real travel data.

Test edge cases including:

- No nearby airports.
- Incorrect airport coordinates.
- Expired flight fares.
- Rate-limit errors.
- Missing credentials.
- Currency mismatches.
- Overnight connections.
- Date changes across time zones.
- Self-transfer feasibility.
- Very short layovers.
- Extremely long layovers.
- Cancelled or changed itinerary data where available.
- High traffic.
- Attraction closed.
- Invalid railway availability.
- Budget exhaustion.
- No viable route.

---

# 14. DEVELOPMENT BEHAVIOR

Before implementing a stage:

1. Inspect the relevant existing code.
2. Review documentation.
3. Outline the implementation approach.
4. Identify dependencies.
5. Identify risks and API costs.

Then implement the stage.

After implementing:

1. Run relevant tests.
2. Resolve failures.
3. Verify behavior.
4. Summarize what was actually completed.
5. List any manual setup needed.
6. Explain remaining limitations.
7. Provide precise instructions to verify the stage.

Never claim a feature is complete unless it actually works.

Do not repeatedly ask me for information already provided in this specification.

For decisions not requiring credentials or money, make sensible engineering choices and proceed.

For credentials, request the necessary key or ask me to add it to an environment file.

Never ask me to paste private API keys into source code.

Never expose secrets in logs, screenshots, commits, or frontend output.

Do not perform paid actions without approval.

---

# 15. REQUIRED OUTPUT AFTER EACH STAGE

At the end of every stage, provide:

**Stage completed:** Name and number.

**Implemented:** Exact features and files changed.

**Test results:** Tests executed and results.

**Live API status:** Providers actually tested, providers awaiting credentials, and known restrictions.

**Cost status:** Which paid/quota-based APIs were used and whether any billable usage may have occurred.

**Manual verification:** How I can test the completed functionality.

**Limitations:** What remains incomplete.

**Next stage:** Name and intended features.

Then stop and wait for my next instruction.

Do not automatically start the next stage.

---

# 16. IMPORTANT FINAL PRODUCT REQUIREMENTS

The final application must:

- Work with actual user travel searches.
- Provide current real flight results where provider access permits.
- Search relevant alternative airports.
- Calculate door-to-door travel.
- Evaluate train connections when legally accessible.
- Never fabricate train seats.
- Account for transfer time.
- Account for traffic where supported.
- Provide understandable route rankings.
- Offer optional long-layover exploration.
- Use Groq only when explicitly requested.
- Protect API credentials.
- Minimize API expenditure.
- Display data freshness.
- Be responsive and practical.
- Use yellow, black, and white styling.
- Contain no gradients or generic AI-looking UI.
- Remain extendable to commercial APIs later.

The system's primary purpose is not to demonstrate that multiple APIs can be called.

Its purpose is to help an actual traveller discover better journeys.

---

# 17. START HERE

Begin with **Stage 0 only**.

Inspect the workspace and establish the architecture and development foundation.

Read the relevant provider documentation and verify current access requirements before choosing implementation details.

Create the initial repository structure and required documentation.

Do not build the complete frontend or integrate all APIs yet.

After finishing Stage 0, present the results and stop.

Wait until I explicitly tell you:

"Continue to Stage 1."
