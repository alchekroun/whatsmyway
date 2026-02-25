# API (Flask)

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Environment variables

- `DATABASE_URL` (optional): defaults to `sqlite:///whatsmyway.db`
- `FLASK_ENV` (optional)
- `LOCATION_PROVIDER` (optional): `geoapify` (default) or `geoapify-haversine`
- `GEOAPIFY_API_KEY` (required for Geoapify providers)
- `GEO_TIMEOUT_SECONDS` (optional): HTTP timeout for geocoding/routing requests, default `8`
- `GEOAPIFY_ROUTE_MODE` (optional): route mode for Geoapify, default `drive`

## Endpoints

- `GET /api/health`
- `GET /api/events?sales_rep_id=...&start=...&end=...`
- `POST /api/events` (address-only input; backend geocodes)
- `POST /api/recommendations` (address-only input; backend geocodes)
