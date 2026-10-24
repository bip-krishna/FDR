# FDR — Multimodal Travel Planner

A production-minded travel planning platform for comparing door-to-door journeys across flights, rail, and ground transfers. It is being built in the stages defined in [plan.md](plan.md).

## Product rules

- Real provider data only. Every result must identify its source, freshness, and whether it is live, cached, estimated, static reference data, or unavailable.
- Missing prices and availability remain unknown; they are never silently replaced with zeroes or fixtures.
- API integrations stay disabled until credentials, access, and explicit quota ceilings are configured.
- Yellow, black, and white are the product palette. Keep the interface crisp, accessible, responsive, and free of gradients.
- No paid plans, billable resources, or hosting subscriptions are activated by this project.

## Project status

**Current stage: Stage 1 — frontend foundation.** The responsive app shell, journey search form, results structure, validation, and honest unavailable states are implemented. No live travel integrations are connected yet.

## Planned structure

- `frontend/`: Next.js App Router, TypeScript, React, Tailwind CSS.
- `backend/`: Python, FastAPI, Pydantic, SQLAlchemy, Alembic.
- `data/`: downloaded, versioned reference-data inputs such as OurAirports.
- `docs/`: architecture, provider access, cost controls, and roadmap.
- `scripts/`: repeatable setup and data maintenance utilities.

## Local development prerequisites

Verified on 2026-10-24: Node.js v26.8.2, npm 11.19.1, Python 3.9.6, and Git 2.50.1. For the current frontend dependencies, use Node.js 22.12+, 24.x, or 26+. For backend development and future hosting, use Python 3.11 or newer; the installed Python 3.9.6 is below the project baseline and should not be used to pin current dependencies.

## Run the frontend

```sh
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Run `npm run test` for validation unit tests, `npm run lint` for linting, and `npm run build` to check the production build.

Stage 1 manual checks and known limitations are in [docs/stage-1.md](docs/stage-1.md).

## Configuration

Copy `.env.example` to a private local `.env` only when beginning provider work. Keep credentials server-side and never commit them. All paid or quota-based integrations are disabled by default.

## Hosting direction

This project is intended to be hosted when deployment is reached. Keep configuration environment-based and avoid localhost assumptions in application code. SQLite is for early development only; hosted deployment should use persistent PostgreSQL. Stage 11 will choose and document a concrete host based on current costs, provider terms, persistence, and operational needs. No hosting account, paid plan, or cloud resource has been enabled.

## Staged delivery

See [docs/roadmap.md](docs/roadmap.md). The source plan requires one stage at a time and a stop for user direction after each stage. Stage 1 is complete; the next stage is airport reference data and location discovery.
