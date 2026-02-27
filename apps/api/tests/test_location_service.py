from __future__ import annotations

import os

import pytest

from app.services.location_service import (
    GeocodingError,
    GeoapifyProvider,
    GeoPoint,
    HaversineRoutingProvider,
    LocationService,
    ProviderConfigurationError,
    RoutingError,
    get_location_service,
)


def test_geoapify_provider_parsing_and_errors(monkeypatch):
    provider = GeoapifyProvider(api_key="x")

    monkeypatch.setattr(
        provider,
        "_get_json",
        lambda *_args, **_kwargs: {
            "features": [{"properties": {"lat": 1.2, "lon": 3.4, "formatted": "A"}}]
        },
    )
    point = provider.geocode("A")
    assert point == GeoPoint(lat=1.2, lng=3.4)
    assert provider.suggest_addresses("A") == ["A"]

    monkeypatch.setattr(provider, "_get_json", lambda *_args, **_kwargs: {"features": []})
    with pytest.raises(GeocodingError):
        provider.geocode("A")

    with pytest.raises(RoutingError):
        provider.estimate_travel_minutes(GeoPoint(1, 1), GeoPoint(2, 2))


def test_location_service_normalize_and_fallback():
    class _Geo:
        def geocode(self, _a: str) -> GeoPoint:
            return GeoPoint(1.0, 2.0)

        def suggest_addresses(self, _q: str, limit: int = 5) -> list[str]:
            return ["x"][:limit]

    class _BrokenRouting:
        def estimate_travel_minutes(self, _o: GeoPoint, _d: GeoPoint) -> float:
            raise RoutingError("no route")

    service = LocationService(_Geo(), _BrokenRouting(), HaversineRoutingProvider())
    assert service.normalize_address("  11   rue  ") == "11 rue"
    assert service.suggest_addresses("ab") == []
    assert service.suggest_addresses("abc") == ["x"]
    minutes = service.estimate_travel_minutes(GeoPoint(48.85, 2.35), GeoPoint(48.86, 2.36))
    assert minutes >= 2.0

    with pytest.raises(ValueError):
        service.normalize_address("   ")


def test_get_location_service_env_branches(monkeypatch):
    get_location_service.cache_clear()
    monkeypatch.setenv("LOCATION_PROVIDER", "geoapify")
    monkeypatch.setenv("GEOAPIFY_API_KEY", "key")
    monkeypatch.setenv("ROUTING_FALLBACK", "off")
    service = get_location_service()
    assert service.fallback_routing_provider is None

    get_location_service.cache_clear()
    monkeypatch.setenv("ROUTING_FALLBACK", "haversine")
    service_fb = get_location_service()
    assert service_fb.fallback_routing_provider is not None

    get_location_service.cache_clear()
    monkeypatch.setenv("ROUTING_FALLBACK", "invalid")
    with pytest.raises(ProviderConfigurationError):
        get_location_service()

    get_location_service.cache_clear()
    monkeypatch.setenv("LOCATION_PROVIDER", "unknown")
    with pytest.raises(ProviderConfigurationError):
        get_location_service()

    get_location_service.cache_clear()
    monkeypatch.setenv("LOCATION_PROVIDER", "geoapify-haversine")
    monkeypatch.setenv("GEOAPIFY_API_KEY", "key")
    service_h = get_location_service()
    assert isinstance(service_h.routing_provider, HaversineRoutingProvider)

    get_location_service.cache_clear()
