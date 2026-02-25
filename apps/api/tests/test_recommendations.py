from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.models.event import SalesEvent
from app.services.recommendation_service import recommend_slots
from app.services.travel_service import estimate_travel_minutes

PARIS_LOCATIONS = [
    ("Louvre Museum", 48.860611, 2.337644),
    ("Notre-Dame", 48.852968, 2.349902),
    ("Eiffel Tower", 48.85837, 2.294481),
    ("Arc de Triomphe", 48.873792, 2.295028),
    ("Gare du Nord", 48.880948, 2.355314),
    ("Place de la Bastille", 48.853041, 2.369139),
    ("Montparnasse Tower", 48.842208, 2.321111),
    ("Place de la République", 48.867368, 2.363091),
    ("Opéra Garnier", 48.8719, 2.3316),
    ("Luxembourg Gardens", 48.846222, 2.33716),
    ("Canal Saint-Martin", 48.8722, 2.3637),
    ("Parc Monceau", 48.879, 2.3094),
    ("La Défense Esplanade", 48.891865, 2.238443),
    ("Bercy Village", 48.8324, 2.3861),
    ("Parc des Buttes-Chaumont", 48.8809, 2.3819),
    ("Place d'Italie", 48.8313, 2.3555),
    ("Trocadéro", 48.8629, 2.2870),
    ("Père Lachaise", 48.8614, 2.3933),
    ("Batignolles", 48.8867, 2.3186),
    ("Sorbonne", 48.8493, 2.3430),
]


def _create_paris_schedule() -> list[SalesEvent]:
    events: list[SalesEvent] = []
    base_hour = 8
    for index, (name, lat, lng) in enumerate(PARIS_LOCATIONS):
        start_hour = base_hour + index // 2
        start_minute = 0 if index % 2 == 0 else 30
        start_at = datetime(2026, 3, 10, start_hour, start_minute)
        end_at = datetime(2026, 3, 10, start_hour, start_minute + 20)
        event = SalesEvent(
            title=f"Visit {name}",
            address=name,
            start_at=start_at,
            end_at=end_at,
            lat=lat,
            lng=lng,
            sales_rep_id="rep-paris",
            time_zone="Europe/Paris",
        )
        db.session.add(event)
        events.append(event)

    db.session.commit()
    return events


def test_get_recommendations_extensive_paris_dataset(app, client):
    with app.app_context():
        events = _create_paris_schedule()

    payload = {
        "date_start": "2026-03-10T08:00:00+01:00",
        "date_end": "2026-03-10T19:00:00+01:00",
        "sales_rep_id": "rep-paris",
        "new_event_duration_min": 25,
        "new_event_address": "Hôtel de Ville",
        "new_event_lat": 48.8566,
        "new_event_lng": 2.3522,
        "buffer_min": 5,
    }

    response = client.post("/api/recommendations", json=payload)
    assert response.status_code == 200

    suggestions = response.get_json()["suggestions"]
    assert 1 <= len(suggestions) <= 10
    assert suggestions == sorted(suggestions, key=lambda item: (item["added_travel_min"], item["start_at"]))

    for suggestion in suggestions:
        start = datetime.fromisoformat(suggestion["start_at"])
        end = datetime.fromisoformat(suggestion["end_at"])
        assert (end - start).total_seconds() == 25 * 60
        assert suggestion["total_travel_min"] >= suggestion["added_travel_min"]
        assert "Inserted between" in suggestion["explanation"]

    event_ids = {event.id for event in events}
    linked_ids = {
        suggestion["before_event_id"]
        for suggestion in suggestions
        if suggestion["before_event_id"] is not None
    } | {
        suggestion["after_event_id"] for suggestion in suggestions if suggestion["after_event_id"] is not None
    }
    assert linked_ids
    assert linked_ids.issubset(event_ids)


def test_recommendations_requires_fields(client):
    response = client.post("/api/recommendations", json={"sales_rep_id": "rep-paris"})
    assert response.status_code == 400
    assert "missing fields" in response.get_json()["error"]


def test_recommend_slots_computes_added_travel_delta(app):
    with app.app_context():
        previous_event = SalesEvent(
            title="Morning",
            address="A",
            start_at=datetime(2026, 3, 11, 9, 0),
            end_at=datetime(2026, 3, 11, 9, 30),
            lat=48.8606,
            lng=2.3376,
            sales_rep_id="rep-x",
        )
        next_event = SalesEvent(
            title="Noon",
            address="B",
            start_at=datetime(2026, 3, 11, 11, 0),
            end_at=datetime(2026, 3, 11, 11, 30),
            lat=48.8738,
            lng=2.2950,
            sales_rep_id="rep-x",
        )

        suggestions = recommend_slots(
            date_start=datetime(2026, 3, 11, 8, 0),
            date_end=datetime(2026, 3, 11, 19, 0),
            events=[previous_event, next_event],
            new_event={"address": "Midpoint", "lat": 48.85837, "lng": 2.294481},
            duration_minutes=30,
            buffer_minutes=10,
        )

    assert suggestions
    best = suggestions[0]

    prev_to_new = estimate_travel_minutes(
        {"lat": previous_event.lat, "lng": previous_event.lng},
        {"lat": 48.85837, "lng": 2.294481},
    )
    new_to_next = estimate_travel_minutes(
        {"lat": 48.85837, "lng": 2.294481},
        {"lat": next_event.lat, "lng": next_event.lng},
    )
    prev_to_next = estimate_travel_minutes(
        {"lat": previous_event.lat, "lng": previous_event.lng},
        {"lat": next_event.lat, "lng": next_event.lng},
    )

    expected_added = round(max(prev_to_new + new_to_next - prev_to_next, 0.0), 1)
    assert best["added_travel_min"] == expected_added
    assert best["before_event_id"] == previous_event.id
    assert best["after_event_id"] == next_event.id
