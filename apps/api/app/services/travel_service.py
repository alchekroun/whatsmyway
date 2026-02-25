import math

AVERAGE_CITY_SPEED_KMH = 35.0
TRAFFIC_MULTIPLIER = 1.2


def _haversine_km(origin_lat, origin_lng, dest_lat, dest_lng):
    radius = 6371.0
    d_lat = math.radians(dest_lat - origin_lat)
    d_lng = math.radians(dest_lng - origin_lng)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(origin_lat))
        * math.cos(math.radians(dest_lat))
        * math.sin(d_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def estimate_travel_minutes(origin, destination):
    distance_km = _haversine_km(
        origin["lat"],
        origin["lng"],
        destination["lat"],
        destination["lng"],
    )
    minutes = distance_km / AVERAGE_CITY_SPEED_KMH * 60 * TRAFFIC_MULTIPLIER
    return round(max(minutes, 2.0), 1)
