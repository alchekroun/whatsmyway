from dateutil.parser import isoparse
from flask import Blueprint, jsonify, request

from app.models.event import SalesEvent
from app.services.location_service import (
    GeocodingError,
    ProviderConfigurationError,
    RoutingError,
)
from app.services.recommendation_service import recommend_slots
from app.services.time_service import to_naive_utc
from app.services.travel_service import geocode_address

bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")


def _parse_datetime(raw_value, field_name):
    try:
        return to_naive_utc(isoparse(raw_value))
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid ISO-8601 datetime string")


def _parse_int(raw_value, field_name):
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer")


@bp.post("")
def get_recommendations():
    payload = request.get_json(force=True)

    required = [
        "date_start",
        "date_end",
        "sales_rep_id",
        "new_event_duration_min",
        "new_event_address",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400

    try:
        date_start = _parse_datetime(payload["date_start"], "date_start")
        date_end = _parse_datetime(payload["date_end"], "date_end")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if date_end <= date_start:
        return jsonify({"error": "date_end must be after date_start"}), 400

    try:
        duration = _parse_int(payload["new_event_duration_min"], "new_event_duration_min")
        buffer_min = _parse_int(payload.get("buffer_min", 10), "buffer_min")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if duration <= 0:
        return jsonify({"error": "new_event_duration_min must be greater than 0"}), 400

    if buffer_min < 0:
        return jsonify({"error": "buffer_min must be greater than or equal to 0"}), 400

    new_event_address = (payload.get("new_event_address") or "").strip()
    if not new_event_address:
        return jsonify({"error": "new_event_address must be a non-empty string"}), 400

    try:
        coordinates = geocode_address(new_event_address)
    except ProviderConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except (GeocodingError, RoutingError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 422

    events = (
        SalesEvent.query.filter_by(sales_rep_id=payload["sales_rep_id"])
        .filter(SalesEvent.start_at >= date_start)
        .filter(SalesEvent.end_at <= date_end)
        .order_by(SalesEvent.start_at.asc())
        .all()
    )

    suggestions = recommend_slots(
        date_start=date_start,
        date_end=date_end,
        events=events,
        new_event={
            "address": new_event_address,
            "lat": coordinates["lat"],
            "lng": coordinates["lng"],
        },
        duration_minutes=duration,
        buffer_minutes=buffer_min,
    )

    return jsonify({"suggestions": suggestions})
