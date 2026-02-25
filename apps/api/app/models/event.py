import uuid
from datetime import datetime
from typing import Any, cast

from sqlalchemy import Float, String

from app.extensions import db


class SalesEvent(db.Model):
    __tablename__ = "sales_events"

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(String(255), nullable=False)
    address = db.Column(String(500), nullable=False)
    start_at = db.Column(db.DateTime(timezone=True), nullable=False)
    end_at = db.Column(db.DateTime(timezone=True), nullable=False)
    lat = db.Column(Float, nullable=False)
    lng = db.Column(Float, nullable=False)
    sales_rep_id = db.Column(String(128), nullable=False, index=True)
    time_zone = db.Column(String(128), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "address": self.address,
            "start_at": cast(datetime, self.start_at).isoformat(),
            "end_at": cast(datetime, self.end_at).isoformat(),
            "lat": self.lat,
            "lng": self.lng,
            "sales_rep_id": self.sales_rep_id,
            "time_zone": self.time_zone,
        }
        return payload
