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
