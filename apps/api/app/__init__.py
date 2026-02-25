from __future__ import annotations

import os
from typing import Any

from flask import Flask, Response, jsonify
from flask_cors import CORS

from app.extensions import db
from app.routes.events import bp as events_bp
from app.routes.recommendations import bp as recommendations_bp


def _load_env_file() -> None:
    env_path: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line: str = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


def create_app() -> Flask:
    _load_env_file()
    app: Flask = Flask(__name__)

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///whatsmyway.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.get("/api/health")
    def healthcheck() -> Response:
        payload: dict[str, Any] = {"status": "ok"}
        return jsonify(payload)

    app.register_blueprint(events_bp)
    app.register_blueprint(recommendations_bp)

    return app
