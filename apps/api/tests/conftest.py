from __future__ import annotations

import os
from collections.abc import Generator

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app() -> Generator:
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    flask_app = create_app()
    flask_app.config.update(TESTING=True)

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
