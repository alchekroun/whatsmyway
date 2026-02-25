import math
from typing import TypedDict

AVERAGE_CITY_SPEED_KMH: float = 35.0
TRAFFIC_MULTIPLIER: float = 1.2


class Location(TypedDict):
    lat: float
    lng: float


def _haversine_km(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> float:
    radius: float = 6371.0
    d_lat: float = math.radians(dest_lat - origin_lat)
    d_lng: float = math.radians(dest_lng - origin_lng)
    a: float = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(origin_lat))
        * math.cos(math.radians(dest_lat))
        * math.sin(d_lng / 2) ** 2
    )
    c: float = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def estimate_travel_minutes(origin: Location, destination: Location) -> float:
    distance_km: float = _haversine_km(
        origin["lat"],
        origin["lng"],
        destination["lat"],
        destination["lng"],
    )
    minutes: float = distance_km / AVERAGE_CITY_SPEED_KMH * 60 * TRAFFIC_MULTIPLIER
    return round(max(minutes, 2.0), 1)
