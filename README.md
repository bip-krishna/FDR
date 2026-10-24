# FDR — Multimodal Travel Planner

A production-minded travel planning platform for comparing door-to-door journeys across flights, rail, and ground transfers. It is being built in the stages defined in [plan.md](plan.md).

## Product rules

- Real provider data only. Every result must identify its source, freshness, and whether it is live, cached, estimated, static reference data, or unavailable.
- Missing prices and availability remain unknown; they are never silently replaced with zeroes or fixtures.
- API integrations stay disabled until credentials, access, and explicit quota ceilings are configured.
- Yellow, black, and white are the product palette. Keep the interface crisp, accessible, responsive, and free of gradients.
- No paid plans, billable resources, or hosting subscriptions are activated by this project.

## Project status

**Current stage: Stage 0 — technical feasibility and foundation.** The initial architecture, provider constraints, cost controls, and staged roadmap are documented under `docs/`. No application screens or live integrations have been implemented yet.

## Planned structure

- `frontend/`: Next.js App Router, TypeScript, React, Tailwind CSS.
- `backend/`: Python, FastAPI, Pydantic, SQLAlchemy, Alembic.
- `data/`: downloaded, versioned reference-data inputs such as OurAirports.
- `docs/`: architecture, provider access, cost controls, and roadmap.
- `scripts/`: repeatable setup and data maintenance utilities.

## Local development prerequisites

Verified on 2026-10-24: Node.js v26.8.2, npm 11.19.1, Python 3.9.6, and Git 2.50.1. Use Node.js 20 or newer for current Next.js releases. For backend development and future hosting, use Python 3.11 or newer; the installed Python 3.9.6 is below the project baseline and should not be used to pin current dependencies.

No package installation is needed for Stage 0. Setup commands will be added when Stage 1 begins.

## Configuration

Copy `.env.example` to a private local `.env` only when beginning provider work. Keep credentials server-side and never commit them. All paid or quota-based integrations are disabled by default.

## Hosting direction

This project is intended to be hosted when deployment is reached. Keep configuration environment-based and avoid localhost assumptions in application code. SQLite is for early development only; hosted deployment should use persistent PostgreSQL. Stage 11 will choose and document a concrete host based on current costs, provider terms, persistence, and operational needs. No hosting account, paid plan, or cloud resource has been enabled.

## Staged delivery

See [docs/roadmap.md](docs/roadmap.md). The source plan requires one stage at a time and a stop for user direction after each stage. Stage 0 is the only stage being implemented now.
