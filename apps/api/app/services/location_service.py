from __future__ import annotations

import json
import math
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Final, Protocol

AVERAGE_CITY_SPEED_KMH: Final[float] = 35.0
TRAFFIC_MULTIPLIER: Final[float] = 1.2
DEFAULT_TIMEOUT_SECONDS: Final[float] = 8.0
DEFAULT_ROUTE_MODE: Final[str] = "drive"
DEFAULT_ROUTING_FALLBACK: Final[str] = "off"


class ProviderConfigurationError(RuntimeError):
    pass


class GeocodingError(RuntimeError):
    pass


class RoutingError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lng: float


class GeocodingProvider(Protocol):
    def geocode(self, address: str) -> GeoPoint: ...


class RoutingProvider(Protocol):
    def estimate_travel_minutes(self, origin: GeoPoint, destination: GeoPoint) -> float: ...


class GeoapifyProvider:
    def __init__(self, api_key: str, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS, mode: str = DEFAULT_ROUTE_MODE):
        if not api_key:
            raise ProviderConfigurationError(
                "GEOAPIFY_API_KEY is required when LOCATION_PROVIDER uses geoapify"
            )

        self.api_key: str = api_key
        self.timeout_seconds: float = timeout_seconds
        self.mode: str = mode

    def _get_json(self, base_url: str, params: dict[str, str]) -> dict[str, Any]:
        query: str = urllib.parse.urlencode({**params, "apiKey": self.api_key})
        request: urllib.request.Request = urllib.request.Request(f"{base_url}?{query}", method="GET")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload_raw: str = response.read().decode("utf-8")
                payload: dict[str, Any] = json.loads(payload_raw)
                return payload
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError("Network read timeout from Geoapify") from exc
        except urllib.error.HTTPError as exc:
            body: str = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc

    def geocode(self, address: str) -> GeoPoint:
        try:
            payload: dict[str, Any] = self._get_json(
                "https://api.geoapify.com/v1/geocode/search",
                {"text": address, "limit": "1"},
            )
        except RuntimeError as exc:
            raise GeocodingError(f"Failed to geocode address '{address}': {exc}") from exc

        features: list[dict[str, Any]] = payload.get("features", [])
        if not features:
            raise GeocodingError(f"No geocoding result found for address '{address}'")

        properties: dict[str, Any] = features[0].get("properties", {})
        lat: Any = properties.get("lat")
        lng: Any = properties.get("lon")
        if lat is None or lng is None:
            raise GeocodingError(f"Invalid geocoding response for address '{address}'")

        return GeoPoint(lat=float(lat), lng=float(lng))

    def estimate_travel_minutes(self, origin: GeoPoint, destination: GeoPoint) -> float:
        waypoints: str = f"{origin.lat},{origin.lng}|{destination.lat},{destination.lng}"

        try:
            payload: dict[str, Any] = self._get_json(
                "https://api.geoapify.com/v1/routing",
                {"waypoints": waypoints, "mode": self.mode},
            )
        except RuntimeError as exc:
            raise RoutingError(f"Failed to estimate route: {exc}") from exc

        features: list[dict[str, Any]] = payload.get("features", [])
        if not features:
            raise RoutingError(
                f"No route returned by Geoapify for mode='{self.mode}' "
                f"origin=({origin.lat},{origin.lng}) destination=({destination.lat},{destination.lng})"
            )

        properties: dict[str, Any] = features[0].get("properties", {})
        travel_seconds: Any = properties.get("time")
        if travel_seconds is None:
            raise RoutingError("Route response did not include travel time")

        return round(max(float(travel_seconds) / 60.0, 2.0), 1)


class HaversineRoutingProvider:
    def _haversine_km(self, origin: GeoPoint, destination: GeoPoint) -> float:
        radius: float = 6371.0
        d_lat: float = math.radians(destination.lat - origin.lat)
        d_lng: float = math.radians(destination.lng - origin.lng)
        a: float = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(origin.lat))
            * math.cos(math.radians(destination.lat))
            * math.sin(d_lng / 2) ** 2
        )
        c: float = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius * c

    def estimate_travel_minutes(self, origin: GeoPoint, destination: GeoPoint) -> float:
        distance_km: float = self._haversine_km(origin, destination)
        minutes: float = distance_km / AVERAGE_CITY_SPEED_KMH * 60 * TRAFFIC_MULTIPLIER
        return round(max(minutes, 2.0), 1)


class LocationService:
    def __init__(
        self,
        geocoding_provider: GeocodingProvider,
        routing_provider: RoutingProvider,
        fallback_routing_provider: RoutingProvider | None = None,
    ):
        self.geocoding_provider: GeocodingProvider = geocoding_provider
        self.routing_provider: RoutingProvider = routing_provider
        self.fallback_routing_provider: RoutingProvider | None = fallback_routing_provider

    @staticmethod
    def normalize_address(address: str) -> str:
        normalized: str = " ".join((address or "").strip().split())
        if not normalized:
            raise ValueError("address must be a non-empty string")
        return normalized

    @lru_cache(maxsize=2048)
    def _cached_geocode(self, normalized_address: str) -> GeoPoint:
        return self.geocoding_provider.geocode(normalized_address)

    def geocode_address(self, address: str) -> GeoPoint:
        normalized: str = self.normalize_address(address)
        return self._cached_geocode(normalized)

    def estimate_travel_minutes(self, origin: GeoPoint, destination: GeoPoint) -> float:
        try:
            return self.routing_provider.estimate_travel_minutes(origin, destination)
        except RoutingError:
            if self.fallback_routing_provider is None:
                raise
            return self.fallback_routing_provider.estimate_travel_minutes(origin, destination)


@lru_cache(maxsize=1)
def get_location_service() -> LocationService:
    provider_name: str = os.getenv("LOCATION_PROVIDER", "geoapify").strip().lower()
    timeout_seconds: float = float(os.getenv("GEO_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    routing_fallback: str = os.getenv("ROUTING_FALLBACK", DEFAULT_ROUTING_FALLBACK).strip().lower()

    if provider_name == "geoapify":
        geoapify: GeoapifyProvider = GeoapifyProvider(
            api_key=os.getenv("GEOAPIFY_API_KEY", "").strip(),
            timeout_seconds=timeout_seconds,
            mode=os.getenv("GEOAPIFY_ROUTE_MODE", DEFAULT_ROUTE_MODE),
        )
        fallback_provider: RoutingProvider | None = (
            HaversineRoutingProvider() if routing_fallback == "haversine" else None
        )
        if routing_fallback not in {"off", "haversine"}:
            raise ProviderConfigurationError(
                f"Unsupported ROUTING_FALLBACK '{routing_fallback}'. Supported values: off, haversine"
            )
        return LocationService(
            geocoding_provider=geoapify,
            routing_provider=geoapify,
            fallback_routing_provider=fallback_provider,
        )

    if provider_name == "geoapify-haversine":
        geoapify = GeoapifyProvider(
            api_key=os.getenv("GEOAPIFY_API_KEY", "").strip(),
            timeout_seconds=timeout_seconds,
            mode=os.getenv("GEOAPIFY_ROUTE_MODE", DEFAULT_ROUTE_MODE),
        )
        return LocationService(geocoding_provider=geoapify, routing_provider=HaversineRoutingProvider())

    raise ProviderConfigurationError(
        f"Unsupported LOCATION_PROVIDER '{provider_name}'. Supported values: geoapify, geoapify-haversine"
    )
