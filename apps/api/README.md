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

## Endpoints

- `GET /api/health`
- `GET /api/events?sales_rep_id=...&start=...&end=...`
- `POST /api/events`
- `POST /api/recommendations`


## Tests

```bash
python -m pytest
```

To snapshot real routing once for the 20-address Paris recommendations dataset and reuse it in tests:

```bash
python tests/scripts/fetch_paris_routes_snapshot.py
```

This writes `tests/data/paris_routes_cache.json`, which is then consumed by `test_recommendations.py` with no per-test API calls.
