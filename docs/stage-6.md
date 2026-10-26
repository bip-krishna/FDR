# Stage 6 — Indian Railways integration

## Implemented

- Added a station discovery API backed by the official Indian Railways *Trains at a Glance 2026* Station Code Index. The bundled CSV contains 808 station names and codes, with the source URL and retrieval date returned in every response.
- Added a Rail Explorer page with station autocomplete, journey-date selection, explicit unavailable states for schedule/fare/seat availability, and links to NTES and IRCTC.
- Added a normalized train-segment contract and a `TrainProvider` interface for a future authorized provider. Segment normalization requires timezone-aware, chronological times and keeps fares and inventory unknown unless a provider supplies separately validated data.
- Added `/api/rail/status`, `/api/rail/stations`, and `/api/rail/search`. Search validates station codes and dates, returns no train offers when no authorized feed is connected, and never invents train schedules, fares, or seats.
- No unofficial scraping, CAPTCHA handling, reverse-engineered endpoints, or train booking flow is included.

## Provider access and cost review

The current IRCTC Train Information Enquiry Services policy (TIES, Edition 2025 v2.1, effective 20 September 2025) is the official route for third-party schedule, trains-between-stations, fare, and accommodation-availability data. It requires IRCTC approval and an agreement. For website integration, the published fees are ₹10 lakh + taxes one-time integration and ₹5 lakh + taxes minimum annual business commitment for general firms, or ₹5 lakh + taxes and ₹2.5 lakh + taxes respectively for qualifying startup/MSME firms. The policy also lists a ₹5 lakh security deposit, ₹0.25 + taxes per successful enquiry, and a ₹1 lakh minimum RDS balance. This project has not applied, signed an agreement, enabled the service, or incurred these charges.

The public Ministry of Railways Open Government Data timetable listing was last updated on 24 January 2018. It is too stale to present as a current train schedule. The current 2026 Indian Railways station-code index is suitable for station discovery, but does not provide route schedules. Therefore live train routes cannot yet be safely included in journey ranking. NTES and IRCTC links let users check authoritative current information directly.

## Verification

Backend tests cover station lookup and provenance, route request validation, unavailable state accuracy, fallback links, and normalized train-segment chronology and unknown fare/availability.

## Sources

- [Indian Railways 2026 Station Code Index](https://rb.indianrailways.gov.in/uploads/directorate/coaching/TAG_2026/Station_Code_Index.pdf)
- [IRCTC TIES Policy, Edition 2025 v2.1](https://contents.irctc.co.in/en/TIES_Policy.pdf)
- [CRIS National Train Enquiry System overview](https://cris.org.in/loadpage?page=proNTES)
- [Ministry of Railways train timetable listing on data.gov.in](https://www.data.gov.in/catalog/indian-railways-train-time-table)
- [NTES](https://enquiry.indianrail.gov.in/mntes/)
- [IRCTC train search](https://www.irctc.co.in/nget/train-search)

## Remaining limitation

The stage establishes station discovery, normalization, provider boundaries, and official fallback links. It does not provide live or static train schedules or fares because no current permitted feed is available for this personal project without IRCTC approval and substantial charges. Add route ranking only after an authorized schedule provider is configured.
