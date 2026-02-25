from __future__ import annotations

from datetime import datetime
from typing import Any

from dateutil.parser import isoparse
from flask import Blueprint, Response, jsonify, request

from app.extensions import db
from app.models.event import SalesEvent
from app.services.time_service import to_naive_utc

bp = Blueprint("events", __name__, url_prefix="/api/events")


@bp.get("")
def list_events() -> tuple[Response, int] | Response:
    sales_rep_id: str | None = request.args.get("sales_rep_id")
    start: str | None = request.args.get("start")
    end: str | None = request.args.get("end")

    if not sales_rep_id or not start or not end:
        return jsonify({"error": "sales_rep_id, start and end are required"}), 400

    start_at: datetime = to_naive_utc(isoparse(start))
    end_at: datetime = to_naive_utc(isoparse(end))

    events: list[SalesEvent] = (
        SalesEvent.query.filter_by(sales_rep_id=sales_rep_id)
        .filter(SalesEvent.start_at >= start_at)
        .filter(SalesEvent.end_at <= end_at)
        .order_by(SalesEvent.start_at.asc())
        .all()
    )

    return jsonify([event.to_dict() for event in events])


@bp.post("")
def create_event() -> tuple[Response, int] | Response:
    payload_raw: Any = request.get_json(force=True)
    if not isinstance(payload_raw, dict):
        return jsonify({"error": "invalid JSON payload"}), 400
    payload: dict[str, Any] = payload_raw

    required: list[str] = [
        "title",
        "address",
        "start_at",
        "end_at",
        "lat",
        "lng",
        "sales_rep_id",
    ]
    missing: list[str] = [key for key in required if key not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400

    start_at: datetime = to_naive_utc(isoparse(str(payload["start_at"])))
    end_at: datetime = to_naive_utc(isoparse(str(payload["end_at"])))
    if end_at <= start_at:
        return jsonify({"error": "end_at must be after start_at"}), 400

    event: SalesEvent = SalesEvent(
        title=str(payload["title"]),
        address=str(payload["address"]),
        start_at=start_at,
        end_at=end_at,
        lat=float(payload["lat"]),
        lng=float(payload["lng"]),
        sales_rep_id=str(payload["sales_rep_id"]),
        time_zone=str(payload.get("time_zone")) if payload.get("time_zone") is not None else None,
    )
    db.session.add(event)
    db.session.commit()

    return jsonify(event.to_dict()), 201
