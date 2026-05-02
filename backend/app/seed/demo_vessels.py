"""Seed ~50 demo vessels (10 deliberately suspicious) for the hackathon demo.

Run with: `make seed`  (or `python -m app.seed.demo_vessels`)
"""

from app.db import SessionLocal, init_db


def seed() -> None:
    """Populate the database with demo vessels, owners, events, and scores."""
    raise NotImplementedError("seed.demo_vessels.seed not implemented yet")


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed()
        print("seeded demo vessels")
    except NotImplementedError as e:
        # Allow `make seed` to exit cleanly while the seeder is still a stub.
        print(f"[stub] {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
