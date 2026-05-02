"""SQLAlchemy engine, session, and declarative base.

Default DB is SQLite for zero-setup hackathon dev. Set DATABASE_URL to a
postgres+psycopg dsn (e.g. when running `docker compose up`) to use
PostgreSQL + PostGIS instead. The application logic is portable; only
geometry storage upgrades from JSON-blob to native PostGIS Geometry once
GeoAlchemy2 is wired up (TODO).
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yield a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called from app startup. No migrations for the hackathon."""
    # Import models so they register with Base.metadata before create_all.
    from app.models import event, evidence, score, vessel  # noqa: F401

    Base.metadata.create_all(bind=engine)
