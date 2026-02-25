from dateutil.parser import isoparse
from flask import Blueprint, jsonify, request

from app.models.event import SalesEvent
from app.services.recommendation_service import recommend_slots
from app.services.time_service import to_naive_utc

bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")


@bp.post("")
def get_recommendations():
    payload = request.get_json(force=True)

    required = [
        "date_start",
        "date_end",
        "sales_rep_id",
        "new_event_duration_min",
        "new_event_lat",
        "new_event_lng",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400

    date_start = to_naive_utc(isoparse(payload["date_start"]))
    date_end = to_naive_utc(isoparse(payload["date_end"]))

    if date_end <= date_start:
        return jsonify({"error": "date_end must be after date_start"}), 400

    events = (
        SalesEvent.query.filter_by(sales_rep_id=payload["sales_rep_id"])
        .filter(SalesEvent.start_at >= date_start)
        .filter(SalesEvent.end_at <= date_end)
        .order_by(SalesEvent.start_at.asc())
        .all()
    )

    duration = int(payload["new_event_duration_min"])
    buffer_min = int(payload.get("buffer_min", 10))

    suggestions = recommend_slots(
        date_start=date_start,
        date_end=date_end,
        events=events,
        new_event={
            "address": payload.get("new_event_address", ""),
            "lat": float(payload["new_event_lat"]),
            "lng": float(payload["new_event_lng"]),
        },
        duration_minutes=duration,
        buffer_minutes=buffer_min,
    )

    return jsonify({"suggestions": suggestions})
