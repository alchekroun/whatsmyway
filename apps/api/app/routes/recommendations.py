from __future__ import annotations

from datetime import datetime
from typing import Any

from dateutil.parser import ParserError, isoparse
from flask import Blueprint, Response, jsonify, request

from app.models.event import SalesEvent
from app.services.location_service import (
    GeocodingError,
    ProviderConfigurationError,
    RoutingError,
    get_location_service,
)
from app.services.recommendation_service import RecommendationResult, recommend_slots
from app.services.time_service import to_naive_utc

bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")


@bp.post("")
def get_recommendations() -> tuple[Response, int] | Response:
    payload_raw: Any = request.get_json(force=True)
    if not isinstance(payload_raw, dict):
        return jsonify({"error": "invalid JSON payload"}), 400
    payload: dict[str, Any] = payload_raw

    required: list[str] = [
        "date_start",
        "date_end",
        "sales_rep_id",
        "new_event_duration_min",
        "new_event_address",
    ]
    missing: list[str] = [key for key in required if key not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400

    try:
        date_start: datetime = to_naive_utc(isoparse(str(payload["date_start"])))
        date_end: datetime = to_naive_utc(isoparse(str(payload["date_end"])))
    except (TypeError, ValueError, ParserError):
        return jsonify({"error": "date_start and date_end must be valid ISO datetime values"}), 400

    if date_end <= date_start:
        return jsonify({"error": "date_end must be after date_start"}), 400

    try:
        duration: int = int(payload["new_event_duration_min"])
    except (TypeError, ValueError):
        return jsonify({"error": "new_event_duration_min must be an integer"}), 400
    if duration <= 0:
        return jsonify({"error": "new_event_duration_min must be positive"}), 400

    try:
        buffer_min: int = int(payload.get("buffer_min", 10))
    except (TypeError, ValueError):
        return jsonify({"error": "buffer_min must be an integer"}), 400
    if buffer_min < 0:
        return jsonify({"error": "buffer_min must be zero or positive"}), 400

    address: str = str(payload["new_event_address"]).strip()
    if not address:
        return jsonify({"error": "new_event_address must be non-empty"}), 400

    sales_rep_id: str = str(payload["sales_rep_id"])
    events: list[SalesEvent] = (
        SalesEvent.query.filter_by(sales_rep_id=sales_rep_id)
        .filter(SalesEvent.start_at >= date_start)
        .filter(SalesEvent.end_at <= date_end)
        .order_by(SalesEvent.start_at.asc())
        .all()
    )

    try:
        location_service = get_location_service()
        new_event_point = location_service.geocode_address(address)
        suggestions: list[RecommendationResult] = recommend_slots(
            date_start=date_start,
            date_end=date_end,
            events=events,
            new_event_point=new_event_point,
            new_event_address=address,
            duration_minutes=duration,
            buffer_minutes=buffer_min,
            location_service=location_service,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except (GeocodingError, RoutingError) as exc:
        return jsonify({"error": str(exc)}), 502
    except ProviderConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        return jsonify({"error": "Upstream routing/geocoding provider failure"}), 502

    return jsonify({"suggestions": suggestions})
