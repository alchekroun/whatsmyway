# WhatsMyWay Monorepo

Sales calendar optimization app:
- Frontend: React + TypeScript single page app (`apps/frontend`)
- Backend: Flask API (`apps/api`)
- Shared contracts: TS types package (`packages/shared-types`)

## Development Plan

1. Domain and constraints:
   - Event storage, date range, travel-aware insertion objective.
2. Core API and algorithm:
   - Create/list events and recommend best insertion slots by added travel time.
3. Frontend workflow:
   - Load events, add events, request ranked suggestions.
4. Integrations:
   - Replace distance estimator with external routing/geocoding providers.
5. Hardening:
   - Auth, rate limiting, validation, telemetry.
6. Scale-up:
   - Postgres production DB + migrations + test suites.

## Repository Layout

```text
apps/
  frontend/   # Vite React SPA
  api/        # Flask API deployed as Vercel Python Function
packages/
  shared-types/
```

## Quick Start

### 1) Frontend

```bash
npm install
cd apps/frontend
cp .env.example .env
npm run dev
```

### 2) API

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Frontend default runs on `http://localhost:5173`, API on `http://localhost:5001`.

## API Contracts

### POST `/api/events`

```json
{
  "title": "Client visit",
  "address": "123 Main St",
  "start_at": "2026-02-25T09:00:00-05:00",
  "end_at": "2026-02-25T10:00:00-05:00",
  "sales_rep_id": "rep-001",
  "time_zone": "America/New_York"
}
```

### POST `/api/recommendations`

```json
{
  "date_start": "2026-02-25T08:00:00-05:00",
  "date_end": "2026-02-26T18:00:00-05:00",
  "sales_rep_id": "rep-001",
  "new_event_duration_min": 45,
  "new_event_address": "789 Park Ave",
  "buffer_min": 10
}
```

Returns ranked candidate slots sorted by minimal added travel time.

## Recommendation Algorithm (v1)

1. Pull events in range sorted by start time.
2. Build free windows between existing events.
3. For each feasible insertion slot:
   - Added travel = `travel(prev->new) + travel(new->next) - travel(prev->next)`
4. Apply duration + buffer constraints.
5. Rank by lowest added travel, then earliest start.

Travel-time and geocoding are provider-backed via a modular location interface (Geoapify by default).

## Vercel Deployment (Monorepo)

Use two Vercel projects pointing to the same repo:

1. Frontend project
   - Root Directory: `apps/frontend`
   - Build command: `npm run build`
   - Output: `dist`
   - Env var: `VITE_API_BASE_URL=https://<api-project>.vercel.app`

2. API project
   - Root Directory: `apps/api`
   - Python runtime function entry: `api/index.py`
   - Env var: `DATABASE_URL=<managed-postgres-url>`

This keeps SPA and API independently deployable while sharing one monorepo.

## Production Notes

- Use managed Postgres (Neon, Supabase, RDS, etc.) for `DATABASE_URL`.
- Replace estimator with provider-backed routing/geocoding for real travel ETAs.
- Add Alembic migrations before production schema changes.
