# FDR — Multimodal Travel Planner

A production-minded travel planning platform for comparing door-to-door journeys across flights, rail, and ground transfers. It is being built in the stages defined in [plan.md](plan.md).

## Product rules

- Real provider data only. Every result must identify its source, freshness, and whether it is live, cached, estimated, static reference data, or unavailable.
- Missing prices and availability remain unknown; they are never silently replaced with zeroes or fixtures.
- API integrations stay disabled until credentials, access, and explicit quota ceilings are configured.
- Yellow, black, and white are the product palette. Keep the interface crisp, accessible, responsive, and free of gradients.
- No paid plans, billable resources, or hosting subscriptions are activated by this project.

## Project status

**Current stage: Stage 3 — live flight search.** The backend has a SerpApi Google Flights adapter, normalized one-way offers, bounded alternative-airport search, and persistent usage controls. Live searches remain disabled until a key, an account-specific cap, and a cost estimate are configured.

## Planned structure

- `frontend/`: Next.js App Router, TypeScript, React, Tailwind CSS.
- `backend/`: Python, FastAPI, Pydantic, SQLAlchemy, Alembic.
- `data/`: downloaded, versioned reference-data inputs such as OurAirports.
- `docs/`: architecture, provider access, cost controls, and roadmap.
- `scripts/`: repeatable setup and data maintenance utilities.

## Local development prerequisites

Verified on 2026-10-24: Node.js v26.8.2, npm 11.19.1, Python 3.11.16, Python 3.9.6, and Git 2.50.1. For the current frontend dependencies, use Node.js 22.12+, 24.x, or 26+. Use Python 3.11 or newer for the backend.

## Run the frontend

```sh
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Run `npm run test` for validation unit tests, `npm run lint` for linting, and `npm run build` to check the production build.

Stage 1 checks are in [docs/stage-1.md](docs/stage-1.md). Stage 2 setup and API details are in [docs/stage-2.md](docs/stage-2.md).

## Run the backend

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m app.import_airports
../.venv/bin/python -m uvicorn app.main:app --reload
```

The API listens on `http://localhost:8000`; its OpenAPI page is `/docs`. Refresh `data/airports.csv` from OurAirports before running the importer when you want a newer snapshot. See [data/README.md](data/README.md).

For the frontend, copy `frontend/.env.example` to `frontend/.env.local` and set `NEXT_PUBLIC_FDR_API_URL=http://localhost:8000`. This URL is public and contains no provider credential. When hosted, set it to the deployed API URL and configure `FRONTEND_ORIGINS` to the deployed frontend origin.

## Configuration

Copy `.env.example` to a private local `.env` only when beginning provider work. Keep credentials server-side and never commit them. All paid or quota-based integrations are disabled by default.

## Hosting direction

This project is intended to be hosted when deployment is reached. Keep configuration environment-based and avoid localhost assumptions in application code. SQLite is for early development only; hosted deployment should use persistent PostgreSQL. Stage 11 will choose and document a concrete host based on current costs, provider terms, persistence, and operational needs. No hosting account, paid plan, or cloud resource has been enabled.

## Staged delivery

See [docs/roadmap.md](docs/roadmap.md). The source plan requires one stage at a time and a stop for user direction after each stage. Stage 3 is complete; the next stage is Maps and ground transfers.
