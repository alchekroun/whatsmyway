import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

AVERAGE_CITY_SPEED_KMH = 35.0
TRAFFIC_MULTIPLIER = 1.2


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
    def __init__(self, api_key: str, timeout_seconds: float = 8.0, mode: str = "drive"):
        if not api_key:
            raise ProviderConfigurationError(
                "GEOAPIFY_API_KEY is required when LOCATION_PROVIDER is set to geoapify"
            )

        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.mode = mode

    def _get_json(self, base_url: str, params: dict[str, str]) -> dict:
        query = urllib.parse.urlencode({**params, "apiKey": self.api_key})
        request = urllib.request.Request(f"{base_url}?{query}", method="GET")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc

    def geocode(self, address: str) -> GeoPoint:
        try:
            payload = self._get_json(
                "https://api.geoapify.com/v1/geocode/search",
                {"text": address, "limit": "1"},
            )
        except RuntimeError as exc:
            raise GeocodingError(f"Failed to geocode address '{address}': {exc}") from exc

        features = payload.get("features", [])
        if not features:
            raise GeocodingError(f"No geocoding result found for address '{address}'")

        properties = features[0].get("properties", {})
        lat = properties.get("lat")
        lng = properties.get("lon")
        if lat is None or lng is None:
            raise GeocodingError(f"Invalid geocoding response for address '{address}'")

        return GeoPoint(lat=float(lat), lng=float(lng))

    def estimate_travel_minutes(self, origin: GeoPoint, destination: GeoPoint) -> float:
        waypoints = f"{origin.lat},{origin.lng}|{destination.lat},{destination.lng}"

        try:
            payload = self._get_json(
                "https://api.geoapify.com/v1/routing",
                {"waypoints": waypoints, "mode": self.mode},
            )
        except RuntimeError as exc:
            raise RoutingError(f"Failed to estimate route: {exc}") from exc

        features = payload.get("features", [])
        if not features:
            raise RoutingError("No route returned by Geoapify")

        properties = features[0].get("properties", {})
        travel_seconds = properties.get("time")
        if travel_seconds is None:
            # Geoapify can return richer structures; fail explicitly if expected value is absent.
            raise RoutingError("Route response did not include travel time")

        return round(max(float(travel_seconds) / 60.0, 2.0), 1)


class HaversineRoutingProvider:
    def _haversine_km(self, origin: GeoPoint, destination: GeoPoint) -> float:
        radius = 6371.0
        d_lat = math.radians(destination.lat - origin.lat)
        d_lng = math.radians(destination.lng - origin.lng)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(origin.lat))
            * math.cos(math.radians(destination.lat))
            * math.sin(d_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius * c

    def estimate_travel_minutes(self, origin: GeoPoint, destination: GeoPoint) -> float:
        distance_km = self._haversine_km(origin, destination)
        minutes = distance_km / AVERAGE_CITY_SPEED_KMH * 60 * TRAFFIC_MULTIPLIER
        return round(max(minutes, 2.0), 1)


class LocationService:
    def __init__(self, geocoding_provider: GeocodingProvider, routing_provider: RoutingProvider):
        self.geocoding_provider = geocoding_provider
        self.routing_provider = routing_provider

    @staticmethod
    def normalize_address(address: str) -> str:
        normalized = " ".join((address or "").strip().split())
        if not normalized:
            raise ValueError("address must be a non-empty string")
        return normalized

    @lru_cache(maxsize=2048)
    def _cached_geocode(self, normalized_address: str) -> GeoPoint:
        return self.geocoding_provider.geocode(normalized_address)

    def geocode_address(self, address: str) -> GeoPoint:
        normalized = self.normalize_address(address)
        return self._cached_geocode(normalized)

    def estimate_travel_minutes(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return self.routing_provider.estimate_travel_minutes(origin, destination)


@lru_cache(maxsize=1)
def get_location_service() -> LocationService:
    provider_name = os.getenv("LOCATION_PROVIDER", "geoapify").strip().lower()

    if provider_name == "geoapify":
        geoapify = GeoapifyProvider(
            api_key=os.getenv("GEOAPIFY_API_KEY", "").strip(),
            timeout_seconds=float(os.getenv("GEO_TIMEOUT_SECONDS", "8")),
            mode=os.getenv("GEOAPIFY_ROUTE_MODE", "drive"),
        )
        return LocationService(geocoding_provider=geoapify, routing_provider=geoapify)

    if provider_name == "geoapify-haversine":
        geoapify = GeoapifyProvider(
            api_key=os.getenv("GEOAPIFY_API_KEY", "").strip(),
            timeout_seconds=float(os.getenv("GEO_TIMEOUT_SECONDS", "8")),
        )
        return LocationService(geocoding_provider=geoapify, routing_provider=HaversineRoutingProvider())

    raise ProviderConfigurationError(
        f"Unsupported LOCATION_PROVIDER '{provider_name}'. Supported values: geoapify, geoapify-haversine"
    )
