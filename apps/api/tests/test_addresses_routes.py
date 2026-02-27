from __future__ import annotations

from app.services.location_service import GeocodingError, ProviderConfigurationError


class _FakeLocationService:
    def suggest_addresses(self, query: str, limit: int = 5) -> list[str]:
        return [f"{query} A", f"{query} B"][:limit]

    def geocode_address(self, address: str):
        if address == "bad":
            raise GeocodingError("bad address")
        return object()

    def normalize_address(self, address: str) -> str:
        return " ".join(address.strip().split())


def test_suggest_addresses_short_query(client):
    response = client.get("/api/addresses/suggest", query_string={"q": "ab"})
    assert response.status_code == 200
    assert response.get_json() == {"suggestions": []}


def test_suggest_addresses_success(client, monkeypatch):
    monkeypatch.setattr("app.routes.addresses.get_location_service", lambda: _FakeLocationService())
    response = client.get("/api/addresses/suggest", query_string={"q": "Paris"})
    assert response.status_code == 200
    assert response.get_json()["suggestions"] == ["Paris A", "Paris B"]


def test_suggest_addresses_provider_errors(client, monkeypatch):
    def _raise_config():
        raise ProviderConfigurationError("missing key")

    monkeypatch.setattr("app.routes.addresses.get_location_service", _raise_config)
    response = client.get("/api/addresses/suggest", query_string={"q": "Paris"})
    assert response.status_code == 503


def test_validate_address_invalid_payload(client):
    response = client.post("/api/addresses/validate", json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "address is required"


def test_validate_address_success_and_geocoding_error(client, monkeypatch):
    monkeypatch.setattr("app.routes.addresses.get_location_service", lambda: _FakeLocationService())

    ok = client.post("/api/addresses/validate", json={"address": "  11 rue Lalo Paris  "})
    assert ok.status_code == 200
    assert ok.get_json() == {"valid": True, "normalized_address": "11 rue Lalo Paris"}

    bad = client.post("/api/addresses/validate", json={"address": "bad"})
    assert bad.status_code == 502
    assert "bad address" in bad.get_json()["error"]
