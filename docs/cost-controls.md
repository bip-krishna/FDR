# API cost and usage controls

The desired application API spend is ₹0 wherever practical. Free quotas are ceilings to protect, not reasons to use them. No subscription, payment method, billing account, paid service, or hosted resource has been enabled by this setup.

## Default-deny configuration

All provider switches default to false. A request is denied before network access when its provider is disabled, credentials are absent, the request would exceed its configured budget, or a cost cannot be estimated safely under the configured policy.

`MONTHLY_EXTERNAL_API_BUDGET_INR=0` means no billable usage is authorized. Free-tier calls still require explicit enablement, request limits, and provider terms review.

## Required controls before any provider implementation

1. **Per-provider daily and monthly request ceilings** plus a global monthly ceiling.
2. **Estimated-cost ceiling** by provider/SKU and currency, with a conservative conversion source if provider charges are not INR.
3. **Preflight quota gate** before every external call; no call if estimated usage exceeds the remaining allowance.
4. **Per-search fan-out bound**, especially for airport pair expansion. Initial flight cap: four calls per user search, with a smaller default configured until Stage 3.
5. **Places and AI action limits**: at most ten place lookups per layover and one AI call, only after an explicit user action.
6. **Timeouts**, bounded retries, request deduplication, and caching only where provider terms allow.
7. **Usage ledger** by provider, operation, SKU estimate, status, timestamp, and request fingerprint. Avoid persisting sensitive trip details unnecessarily.
8. **Hard disable switch** per provider and a global kill switch.
9. **Fail closed** on unknown prices/SKUs, exhausted quotas, missing usage data, or provider errors. Never substitute mock data.

Google Maps published budgets/alerts are notifications, not guaranteed caps. Configure daily quota limits where available and enforce an independent app-side limit. A Google Maps free monthly SKU cap is not proof that a particular account qualifies or that all requested features remain free.

SerpApi's current published Free plan lists 250 successful searches/month. Other plans are paid; the app must not upgrade or exceed the selected plan allowance.

Amadeus production calls beyond each API's free monthly quota are billed. Remain in a clearly labeled test environment until production access and data quality are explicitly configured; test results must not appear as current fares.

Open-Meteo free endpoint terms are for non-commercial use and specify rate limits and attribution. Reassess before advertising, subscription, or other commercialization.

## Initial environment policy

See `.env.example`: providers start disabled, budget is zero, and per-provider limits are zero. Stages may raise a limit only after reviewing current official terms and documenting why that call is needed. No production secret belongs in this repository.
