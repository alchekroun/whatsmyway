from app.services.location_service import GeoPoint, get_location_service


def geocode_address(address: str) -> dict[str, float]:
    point = get_location_service().geocode_address(address)
    return {"lat": point.lat, "lng": point.lng}


def estimate_travel_minutes(origin: dict[str, float], destination: dict[str, float]) -> float:
    origin_point = GeoPoint(lat=float(origin["lat"]), lng=float(origin["lng"]))
    destination_point = GeoPoint(lat=float(destination["lat"]), lng=float(destination["lng"]))
    return get_location_service().estimate_travel_minutes(origin_point, destination_point)
