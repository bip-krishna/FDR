# Stage 2 — Airport reference and discovery

## Implemented

- Downloaded the OurAirports airport CSV snapshot on 2026-10-24 and recorded provenance in `data/README.md`. The CSV contains 86,280 source records and is retained as the refreshable source input; the generated SQLite index is ignored by Git and rebuilt with the importer.
- Added a SQLAlchemy airport model and indexed code, name, municipality, and service fields. The importer preserves nullable codes and coordinates, airport type, and the source's yes/no/unknown scheduled-service value.
- Added FastAPI endpoints:
  - `GET /health` — backend and dataset readiness.
  - `GET /api/airports?q=Delhi` — airport name and code prefix search plus municipality matching; by default, only records marked scheduled-service yes and passenger-airport types are returned. Set `scheduled_service_only=false` to inspect all matching source records.
  - `GET /api/airports/iata/DEL` — exact, case-insensitive three-letter IATA lookup.
  - `GET /api/airports/nearby?lat=28.6&lon=77.2&radius_km=250` — Haversine distance ranking, closest first; defaults to the same service eligibility filter.
- Responses include source and snapshot date, coordinates, codes, service status, an explicit eligibility flag, and an explanation. Missing IATA codes and coordinates remain null. A source service flag is evidence from OurAirports, not a guarantee of passenger operations.
- Added isolated tests for known-style IATA lookup, missing/invalid codes, city search, non-service and non-passenger filtering, coordinate absence, nearby ranking, and invalid geographic inputs. Test-only airport rows are fixtures and are not used by runtime code.

## Run and verify

From the project root:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m app.import_airports
../.venv/bin/python -m pytest -q
../.venv/bin/python -m uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for the interactive API reference. Example calls:

```sh
curl 'http://localhost:8000/api/airports?q=Delhi'
curl 'http://localhost:8000/api/airports/iata/DEL'
curl 'http://localhost:8000/api/airports/nearby?lat=28.556&lon=77.095&radius_km=250'
```

## Verification status

- Source download and CSV inspection: completed. The source snapshot has 86,280 rows, including 4,336 airports marked with scheduled service.
- `python -m app.import_airports` — passed; imported all 86,280 rows into SQLite.
- `python -m pytest -q` — passed; 6 API tests.
- HTTP smoke check against the downloaded database — `/health`, Delhi lookup, DEL lookup, and nearby ranking all returned 200; Delhi resolves to Indira Gandhi International Airport.
- Pytest reported a Starlette/httpx deprecation notice and a sandbox cache-write warning. They do not affect the passing API tests; the cache warning is specific to this checkout's write restrictions.
- Frontend tests from Stage 1 were not rerun because Stage 2 did not change frontend files.

## Limitations

- The initial API is airport discovery only. Stage 2 does not call flight, mapping, railway, weather, or AI providers and therefore makes no fare, schedule, transfer, or availability claims.
- Airport names and codes use prefix matching; municipality search supports interior matches for alternate city-name forms. Typo-tolerant search is not implemented.
- The CSV is a point-in-time source snapshot. Refresh it and rerun the importer to update records; responses identify the snapshot date.
- Hosting is not configured. The database URL is environment-configurable for later hosted deployment, but public hosting and production database setup remain in Stage 11.
