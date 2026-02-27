from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.models.event import SalesEvent
from app.services.location_service import GeocodingError, ProviderConfigurationError, RoutingError


class _RouteLocationService:
    def __init__(self, *, geocode_error: Exception | None = None, route_error: Exception | None = None):
        self.geocode_error = geocode_error
        self.route_error = route_error

    def geocode_address(self, address: str):
        if self.geocode_error is not None:
            raise self.geocode_error

        class P:
            lat = 48.8566
            lng = 2.3522

        return P()

    def estimate_travel_minutes(self, origin, destination):
        if self.route_error is not None:
            raise self.route_error
        return 7.0


def test_recommendations_invalid_types_and_values(client):
    payload = {
        "date_start": "2026-03-10T08:00:00Z",
        "date_end": "2026-03-10T19:00:00Z",
        "sales_rep_id": "rep",
        "new_event_duration_min": "x",
        "new_event_address": "A",
    }
    r = client.post("/api/recommendations", json=payload)
    assert r.status_code == 400
    assert "must be an integer" in r.get_json()["error"]

    payload["new_event_duration_min"] = 10
    payload["buffer_min"] = -1
    r2 = client.post("/api/recommendations", json=payload)
    assert r2.status_code == 400
    assert "zero or positive" in r2.get_json()["error"]


def test_recommendations_provider_failures(client, monkeypatch):
    base = {
        "date_start": "2026-03-10T08:00:00Z",
        "date_end": "2026-03-10T19:00:00Z",
        "sales_rep_id": "rep",
        "new_event_duration_min": 10,
        "new_event_address": "A",
    }

    monkeypatch.setattr(
        "app.routes.recommendations.get_location_service",
        lambda: _RouteLocationService(geocode_error=GeocodingError("geo bad")),
    )
    r_geo = client.post("/api/recommendations", json=base)
    assert r_geo.status_code == 502

    monkeypatch.setattr(
        "app.routes.recommendations.get_location_service",
        lambda: _RouteLocationService(geocode_error=ProviderConfigurationError("missing key")),
    )
    r_conf = client.post("/api/recommendations", json=base)
    assert r_conf.status_code == 503


def test_recommendations_success_with_route_error_handling(app, client, monkeypatch):
    with app.app_context():
        db.session.add(
            SalesEvent(
                title="Morning",
                address="A",
                start_at=datetime(2026, 3, 10, 9, 0),
                end_at=datetime(2026, 3, 10, 10, 0),
                lat=48.85,
                lng=2.35,
                sales_rep_id="rep",
                time_zone="Europe/Paris",
            )
        )
        db.session.commit()

    monkeypatch.setattr("app.routes.recommendations.get_location_service", lambda: _RouteLocationService())

    payload = {
        "date_start": "2026-03-10T08:00:00Z",
        "date_end": "2026-03-10T19:00:00Z",
        "sales_rep_id": "rep",
        "new_event_duration_min": 30,
        "new_event_address": "Test",
    }
    ok = client.post("/api/recommendations", json=payload)
    assert ok.status_code == 200
    assert "suggestions" in ok.get_json()
