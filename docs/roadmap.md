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

## Stage 3 — Live flight search

Implement the SerpApi adapter and production search path, provenance, quota ledger, normalization, and shortlist-based airport alternatives. Require credentials and stop before exceeding configured limits.

## Stage 4 — Maps and ground transfers

Implement selected Google Routes/Geocoding/Places capabilities only after SKU, billing, key restrictions, and app-side caps are documented. Add map geometry and provenance-aware transfer estimates.

## Stage 5 — End-to-end flight optimization

Combine airport access, live flights, and destination transfers; validate chronology and show known versus unknown prices and clear coverage.

## Stage 6 — Rail integration

Verify an authorized provider and its production access; otherwise provide official enquiry links and explicit unavailable seat status. No unauthorized scraping.

## Stage 7 — Multimodal optimization

Combine verified flight, rail, and ground adapters in a time-dependent bounded search with transfer and self-transfer risk.

## Stage 8 — Deterministic Layover Explorer

Calculate conservative usable windows, return buffers, and verified place feasibility; unknown exit/immigration eligibility remains unverified.

## Stage 9 — Optional Groq assistance

Call only after user action, on verified candidates, validate structured output, and re-check safety constraints deterministically.

## Stage 10 — Personal-use improvements

Add persistent saved journeys, search history, health/usage views, caching, warnings, and optional dark mode without hidden repeated requests.

## Stage 11 — Testing and deployment readiness

Run requested unit/integration/browser/accessibility/security/timezone checks, harden provider failure and quota paths, choose a low-cost host, provision persistent production database configuration, and document deployment and rollback. Do not buy or activate paid resources without user approval.

## Stage 12 — Funding and demonstration preparation

Prepare truthful technical and funding materials using reproducible real-data case studies only. Distinguish implemented capability from roadmap and disclose source coverage and timestamps.
