import os

from flask import Flask, jsonify
from flask_cors import CORS

from app.extensions import db
from app.routes.events import bp as events_bp
from app.routes.recommendations import bp as recommendations_bp


def create_app():
    app = Flask(__name__)

    database_url = os.getenv("DATABASE_URL", "sqlite:///whatsmyway.db")
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
    def healthcheck():
        return jsonify({"status": "ok"})

    app.register_blueprint(events_bp)
    app.register_blueprint(recommendations_bp)

    return app
