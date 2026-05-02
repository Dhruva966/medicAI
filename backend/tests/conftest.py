"""Per-test database isolation.

Each test function gets a fresh SQLite database (via tmp_path) so seeding,
scoring, and other mutations don't bleed between tests.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import db as db_module
from app.db import Base
from app.models import event, evidence, score, vessel  # noqa: F401 — register models


@pytest.fixture
def fresh_db(tmp_path, monkeypatch) -> Iterator[None]:
    """Point the app at a brand-new SQLite file for the duration of the test."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", SessionLocal)

    yield

    engine.dispose()
