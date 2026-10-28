# Development roadmap

The controlling instructions are in `plan.md`. Implement exactly one stage at a time, verify it, report the required status, and stop for the user's instruction before proceeding.

## Stage 0 — Technical feasibility and foundation (complete)

- Inspect workspace and toolchain; establish Git and architecture.
- Record provider access, credentials, legal terms, and cost gates.
- Create README, architecture, integrations, cost controls, roadmap, env example, and initial structure.
- No UI or live API integration.

## Stage 1 — Frontend foundation (complete)

Built a responsive Next.js shell and yellow/black/white design system, search form, app navigation, results page structure, validation, and honest loading, error, and empty states. No example fares. Eight validation unit tests, lint, production build, valid/invalid search behavior, navigation, and a 390px mobile viewport were checked. See [stage-1.md](stage-1.md).

## Stage 2 — Airport reference and discovery (implementation complete; runtime verification pending)

Downloaded the dated OurAirports CSV snapshot, indexed 86,280 airport records into SQLite, and added search, IATA lookup, Haversine nearby ranking, eligibility filters, and FastAPI endpoints. Data source and retrieval date are recorded. See [stage-2.md](stage-2.md).

## Stage 3 — Live flight search (implemented; live account verification pending)

Added the SerpApi adapter and one-way search path, provenance, durable quota ledger, normalization, and bounded airport alternatives. The local environment has no provider credentials and all request caps remain zero; the API correctly refuses live calls until configured. Tests use isolated fixtures and mocked provider transport only. See [stage-3.md](stage-3.md).

## Stage 4 — Maps and ground transfers (implemented; account verification pending)

Added deliberate Geocoding and traffic-aware Routes requests, separate SKU estimates and caps, shared budget reservations, route geometry rendering, traffic labels, and failure states. No key or quotas are configured, so the provider remains unavailable. See [stage-4.md](stage-4.md).

## Stage 5 — End-to-end flight optimization (implemented; live account verification pending)

Added bounded on-demand airport access estimates, time-zone conversion, door-to-door elapsed-time estimates, four ranking modes, known/unknown cost disclosure, risks, sources, and booking links. Google calls remain disabled until key, quotas, and costs are configured. See [stage-5.md](stage-5.md).

## Stage 6 — Rail integration (implemented; live schedule access unavailable)

Added official 2026 station discovery, the provider contract and normalized segment shape, route validation, explicit unavailable states, and NTES/IRCTC fallbacks. Current route schedules, fares, and inventory are not available without IRCTC approval and costly TIES commitments; no unofficial scraping is used. See [stage-6.md](stage-6.md).

## Stage 7 — Multimodal optimization (implemented; feed coverage limited)

Added a bounded time-dependent graph, UTC flight timestamps, transfer buffers, Pareto handling, route risks, and an explicit optimizer action from assessed flight offers and ground-access estimates. The engine accepts train/ground edges, but no train feed or intermediate airport/station transfer estimate is connected, so production routes use flight offers and outer airport-access legs only. Ground fares remain unknown. See [stage-7.md](stage-7.md).

## Stage 8 — Deterministic Layover Explorer (core implemented; provider integration pending)

Added timezone-aware layover duration and conservative exploration-window calculations, a configurable airport return deadline, exit/baggage warnings, and a screen for manual connection times. Unknown exit/immigration eligibility never authorizes leaving. Google Places discovery, traffic-aware attraction feasibility, and weather are explicitly unavailable until their providers and per-SKU cost/request guards are configured. See [stage-8.md](stage-8.md). Stage 8 acceptance criteria are not yet complete.

## Stage 9 — Optional Groq assistance (guarded integration implemented; end-to-end pending)

Added a user-triggered Groq adapter with strict structured output, a candidate-ID-only response contract, backend revalidation, and daily/monthly/per-layover cost guards. The public planner refuses to accept browser-supplied candidate facts and returns before calling Groq because Stage 8 has no verified Places + Routes feed yet. Stage 9 acceptance is not complete. See [stage-9.md](stage-9.md).

## Stage 10 — Personal-use improvements

Add persistent saved journeys, search history, health/usage views, caching, warnings, and optional dark mode without hidden repeated requests.

## Stage 11 — Testing and deployment readiness

Run requested unit/integration/browser/accessibility/security/timezone checks, harden provider failure and quota paths, choose a low-cost host, provision persistent production database configuration, and document deployment and rollback. Do not buy or activate paid resources without user approval.

## Stage 12 — Funding and demonstration preparation

Prepare truthful technical and funding materials using reproducible real-data case studies only. Distinguish implemented capability from roadmap and disclose source coverage and timestamps.
