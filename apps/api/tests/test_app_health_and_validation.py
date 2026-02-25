from __future__ import annotations


def test_healthcheck(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_recommendations_rejects_invalid_range(client):
    payload = {
        "date_start": "2026-03-10T12:00:00Z",
        "date_end": "2026-03-10T11:00:00Z",
        "sales_rep_id": "rep-paris",
        "new_event_duration_min": 30,
        "new_event_lat": 48.8566,
        "new_event_lng": 2.3522,
    }
    response = client.post("/api/recommendations", json=payload)
    assert response.status_code == 400
    assert response.get_json()["error"] == "date_end must be after date_start"
