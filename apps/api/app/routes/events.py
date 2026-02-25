from dateutil.parser import isoparse
from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.event import SalesEvent
from app.services.location_service import (
    GeocodingError,
    ProviderConfigurationError,
    RoutingError,
)
from app.services.time_service import to_naive_utc
from app.services.travel_service import geocode_address

bp = Blueprint("events", __name__, url_prefix="/api/events")


def _parse_datetime(raw_value, field_name):
    try:
        return to_naive_utc(isoparse(raw_value))
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid ISO-8601 datetime string")


@bp.get("")
def list_events():
    sales_rep_id = request.args.get("sales_rep_id")
    start = request.args.get("start")
    end = request.args.get("end")

    if not sales_rep_id or not start or not end:
        return jsonify({"error": "sales_rep_id, start and end are required"}), 400

    try:
        start_at = _parse_datetime(start, "start")
        end_at = _parse_datetime(end, "end")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    events = (
        SalesEvent.query.filter_by(sales_rep_id=sales_rep_id)
        .filter(SalesEvent.start_at >= start_at)
        .filter(SalesEvent.end_at <= end_at)
        .order_by(SalesEvent.start_at.asc())
        .all()
    )

    return jsonify([event.to_dict() for event in events])


@bp.post("")
def create_event():
    payload = request.get_json(force=True)

    required = ["title", "address", "start_at", "end_at", "sales_rep_id"]
    missing = [key for key in required if key not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400

    title = (payload.get("title") or "").strip()
    address = (payload.get("address") or "").strip()
    if not title:
        return jsonify({"error": "title must be a non-empty string"}), 400
    if not address:
        return jsonify({"error": "address must be a non-empty string"}), 400

    try:
        start_at = _parse_datetime(payload["start_at"], "start_at")
        end_at = _parse_datetime(payload["end_at"], "end_at")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if end_at <= start_at:
        return jsonify({"error": "end_at must be after start_at"}), 400

    try:
        coordinates = geocode_address(address)
    except ProviderConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except (GeocodingError, RoutingError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 422

    event = SalesEvent(
        title=title,
        address=address,
        start_at=start_at,
        end_at=end_at,
        lat=coordinates["lat"],
        lng=coordinates["lng"],
        sales_rep_id=payload["sales_rep_id"],
        time_zone=payload.get("time_zone"),
    )
    db.session.add(event)
    db.session.commit()

    return jsonify(event.to_dict()), 201
