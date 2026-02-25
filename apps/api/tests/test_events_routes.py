from __future__ import annotations


def test_create_event_and_list_events(client):
    payload = {
        "title": "Client Visit",
        "address": "10 Rue de Rivoli, Paris",
        "start_at": "2026-03-01T09:00:00+01:00",
        "end_at": "2026-03-01T10:00:00+01:00",
        "lat": 48.8556,
        "lng": 2.3572,
        "sales_rep_id": "rep-paris",
        "time_zone": "Europe/Paris",
    }

    create_response = client.post("/api/events", json=payload)
    assert create_response.status_code == 201
    event = create_response.get_json()
    assert event["title"] == payload["title"]
    assert event["sales_rep_id"] == payload["sales_rep_id"]

    list_response = client.get(
        "/api/events",
        query_string={
            "sales_rep_id": "rep-paris",
            "start": "2026-03-01T00:00:00Z",
            "end": "2026-03-01T23:59:59Z",
        },
    )
    assert list_response.status_code == 200
    listed_events = list_response.get_json()
    assert len(listed_events) == 1
    assert listed_events[0]["id"] == event["id"]


def test_create_event_rejects_invalid_payload(client):
    response = client.post(
        "/api/events",
        json={
            "title": "Invalid",
            "address": "Nowhere",
            "start_at": "2026-03-01T12:00:00Z",
            "end_at": "2026-03-01T11:00:00Z",
            "lat": 48.86,
            "lng": 2.35,
            "sales_rep_id": "rep-paris",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "end_at must be after start_at"


def test_list_events_requires_query_params(client):
    response = client.get("/api/events")
    assert response.status_code == 400
    assert "sales_rep_id, start and end are required" in response.get_json()["error"]
