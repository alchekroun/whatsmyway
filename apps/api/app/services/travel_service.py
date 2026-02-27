from typing import TypedDict

from app.services.location_service import GeoPoint, HaversineRoutingProvider


class Location(TypedDict):
    lat: float
    lng: float


def estimate_travel_minutes(origin: Location, destination: Location) -> float:
    provider = HaversineRoutingProvider()
    return provider.estimate_travel_minutes(
        GeoPoint(lat=origin["lat"], lng=origin["lng"]),
        GeoPoint(lat=destination["lat"], lng=destination["lng"]),
    )
