from __future__ import annotations

from datetime import datetime
from typing import Any

from dateutil.parser import isoparse
from flask import Blueprint, Response, jsonify, request

from app.models.event import SalesEvent
from app.services.recommendation_service import NewEventLocation, RecommendationResult, recommend_slots
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
        "new_event_lat",
        "new_event_lng",
    ]
    missing: list[str] = [key for key in required if key not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400

    date_start: datetime = to_naive_utc(isoparse(str(payload["date_start"])))
    date_end: datetime = to_naive_utc(isoparse(str(payload["date_end"])))

    if date_end <= date_start:
        return jsonify({"error": "date_end must be after date_start"}), 400

    sales_rep_id: str = str(payload["sales_rep_id"])
    events: list[SalesEvent] = (
        SalesEvent.query.filter_by(sales_rep_id=sales_rep_id)
        .filter(SalesEvent.start_at >= date_start)
        .filter(SalesEvent.end_at <= date_end)
        .order_by(SalesEvent.start_at.asc())
        .all()
    )

    duration: int = int(payload["new_event_duration_min"])
    buffer_min: int = int(payload.get("buffer_min", 10))

    new_event: NewEventLocation = {
        "address": str(payload.get("new_event_address", "")),
        "lat": float(payload["new_event_lat"]),
        "lng": float(payload["new_event_lng"]),
    }

    suggestions: list[RecommendationResult] = recommend_slots(
        date_start=date_start,
        date_end=date_end,
        events=events,
        new_event=new_event,
        duration_minutes=duration,
        buffer_minutes=buffer_min,
    )

    return jsonify({"suggestions": suggestions})
