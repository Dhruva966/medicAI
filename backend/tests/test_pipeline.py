"""End-to-end pipeline test: seed → score → brief → evidence list."""

from app import db as _db
from app.seed.demo_vessels import seed
from app.services import brief_generator, network_builder, scoring


def test_full_pipeline_against_demo_scenario(fresh_db) -> None:
    seed()

    db = _db.SessionLocal()
    try:
        score = scoring.score_vessel(db, "9876543")
        assert score.vessel_imo == "9876543"
        # Hero scenario is curated to land in the critical band.
        assert score.score >= 700, f"hero score should be high, got {score.score}"
        assert score.band in ("high", "critical")
        assert score.recommendation in ("sanctions review", "notify command")

        # Every component name from the rubric should be present.
        names = {c.name for c in score.components}
        for required in (
            "dark_activity",
            "kinematic_anomaly",
            "sts_proximity",
            "sanctions_match",
            "identity_inconsistency",
            "route_plausibility",
        ):
            assert required in names, f"missing component {required}"

        # At least four components should have produced evidence on the hero.
        producing = [c for c in score.components if c.contribution > 0]
        assert len(producing) >= 4, f"expected >=4 firing detectors, got {len(producing)}"

        # Brief
        brief = brief_generator.generate(db, "9876543")
        assert brief.headline
        assert brief.summary
        assert brief.evidence
        assert brief.recommended_action == score.recommendation

        # Ownership graph reaches the sanctioned sister vessel.
        net = network_builder.build(db, "9876543", depth=3)
        node_labels = {n.label for n in net.nodes}
        assert "ATLANTIS PIONEER" in node_labels
        assert any(n.kind == "sanctioned_vessel" for n in net.nodes), \
            "ownership graph should surface a sanctioned sister vessel"
    finally:
        db.close()


def test_clean_vessel_lands_in_low_band(fresh_db) -> None:
    seed()
    db = _db.SessionLocal()
    try:
        from app.models import Vessel
        clean = (
            db.query(Vessel)
            .filter(Vessel.flag.in_(["Norway", "Japan", "United Kingdom", "Greece"]))
            .first()
        )
        assert clean is not None
        score = scoring.score_vessel(db, clean.imo)
        assert score.band in ("low", "medium"), f"clean vessel should not be high/critical, got {score.band}"
    finally:
        db.close()
