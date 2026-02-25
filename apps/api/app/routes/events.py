from dateutil.parser import isoparse
from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models.event import SalesEvent
from app.services.time_service import to_naive_utc

bp = Blueprint("events", __name__, url_prefix="/api/events")


@bp.get("")
def list_events():
    sales_rep_id = request.args.get("sales_rep_id")
    start = request.args.get("start")
    end = request.args.get("end")

    if not sales_rep_id or not start or not end:
        return jsonify({"error": "sales_rep_id, start and end are required"}), 400

    start_at = to_naive_utc(isoparse(start))
    end_at = to_naive_utc(isoparse(end))

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

    required = [
        "title",
        "address",
        "start_at",
        "end_at",
        "lat",
        "lng",
        "sales_rep_id",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400

    start_at = to_naive_utc(isoparse(payload["start_at"]))
    end_at = to_naive_utc(isoparse(payload["end_at"]))
    if end_at <= start_at:
        return jsonify({"error": "end_at must be after start_at"}), 400

    event = SalesEvent(
        title=payload["title"],
        address=payload["address"],
        start_at=start_at,
        end_at=end_at,
        lat=float(payload["lat"]),
        lng=float(payload["lng"]),
        sales_rep_id=payload["sales_rep_id"],
        time_zone=payload.get("time_zone"),
    )
    db.session.add(event)
    db.session.commit()

    return jsonify(event.to_dict()), 201
