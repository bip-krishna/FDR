# API access and integration feasibility

Checked against provider documentation on 2026-10-25. Access, quotas, product terms, and prices can change; reconfirm before each integration stage. This document records documented requirements, not account-specific approval.

## Provider matrix

| Provider | Intended use | Access and data caveats | Cost / activation policy |
|---|---|---|---|
| SerpApi Google Flights | Primary live flight search | Requires SerpApi account and API key. Results and booking options are provider-returned; fares may change and are not guaranteed final bookable prices. | Published plan page currently lists 250 searches/month on Free and paid plans thereafter. Search count is per successful search; do not assume free access persists. Disabled until key and explicit monthly ceiling exist. |
| Amadeus Self-Service | Optional secondary flight source | Test environment has limited data and must never be labeled live production data. Production requires application promotion/access and returns live data when approved. | Free monthly quotas exist, but production overages are billed. Keep production disabled until the specific API's quota, price, payment setup, and account approval are reviewed. |
| Google Maps Platform | Geocoding, Routes, Places, map display | Requires project, API enablement, key, and billing configuration for Routes. SKU varies by requested fields/features; route-matrix billing counts origin-destination elements. Restrict keys by API and application. | Google documents free monthly SKU caps; beyond them pay-as-you-go rates apply. Traffic-aware route features may use a higher SKU. Do not enable by default; configure quotas and a hard app-side cost gate first. Budget alerts alone are not a usage cap. |
| OurAirports | Static airport reference records | Public CSV downloads; data is public domain but carries no guarantee of accuracy. No per-search API calls. Presence in dataset does not establish commercial passenger service. | No API key or direct usage fee documented. Download/update deliberately and retain source/update date. |
| Indian Railways / IRCTC | Train schedules, fares, seat availability | No verified public self-service production API for this project is documented in the current plan. Do not scrape, reverse-engineer, bypass CAPTCHA, or infer availability. Use an authorized provider only after access and terms are verified; otherwise link to official enquiry and mark availability unavailable. | No provider enabled. Any integration needs explicit legal/access review. |
| GroqCloud | Optional layover itinerary organization | API key and account/model access required. Use only after user action, with verified place candidates as input; validate output against deterministic safety constraints. Structured-output support is model-dependent. | Account limits and pricing depend on model/account. Disabled until usage limits are confirmed. Never use for time-critical facts. |
| Open-Meteo | Weather forecasts | Public forecast API. Free API is limited to non-commercial use, with rate limits and attribution under CC BY 4.0. Commercial or promotional future use requires appropriate paid service. Provider disclaims guaranteed accuracy/availability. | No paid access activated. Personal/educational use must stay within published limits; commercialization requires reassessment. |
| Geoapify (optional) | Possible mapping/geocoding fallback | Separate key, terms, quota, and costs; no automatic fallback. | Not selected. Evaluate only if a demonstrated need exists and terms/costs are acceptable. |

## Credentials and readiness

No provider credentials or account statuses have been supplied or tested. Before each integration, document exact environment variables, required account/project steps, production versus test mode, quota, terms, and whether a request may incur cost. Never ask for secrets in chat; the user should configure them in a local ignored `.env` or hosting secret manager.

## Deployment constraints

Public hosting changes the risk profile: restrict keys to deployment origins and required APIs, set provider and cloud quotas, monitor actual SKU usage, and apply an app-side hard budget. Do not assume an advertised free quota or billing alert alone prevents spend. Confirm that each provider's terms permit the intended hosted use before enabling it.
