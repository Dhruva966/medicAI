"""Interdiction-brief generator.

Two paths:
  1. Deterministic template (always works, no API key required).
  2. Anthropic Claude (set ANTHROPIC_API_KEY in backend/.env to enable).

Both paths build a structured InterdictionBrief from current scoring + evidence.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import RiskScore, Vessel
from app.schemas import InterdictionBrief
from app.services import scoring


SYSTEM_PROMPT = """\
You are an intelligence analyst writing a maritime deception interdiction brief
for a coalition naval task force. You ground every claim in the supplied
evidence package. You do not speculate beyond it. You output exactly:

HEADLINE: <one tight line, no more than 14 words>
SUMMARY: <one paragraph, 60-120 words>
EVIDENCE:
- <bullet 1, evidence-grounded>
- <bullet 2>
...
RECOMMENDED ACTION: <one of: monitor | investigate | sanctions review | notify command>
CONFIDENCE: <0.0-1.0>
"""


def _build_evidence_block(score: RiskScore) -> str:
    lines: list[str] = []
    for c in score.components:
        if c.contribution <= 0:
            continue
        lines.append(f"## {c.name} (contribution {c.contribution}/{c.weight})")
        for ev in c.evidence_records:
            lines.append(f"- [{ev.severity}] {ev.title}: {ev.description}")
    return "\n".join(lines) or "(no positive components — vessel looks clean)"


def _deterministic_brief(vessel: Vessel, score: RiskScore) -> InterdictionBrief:
    """Template-based brief that always works."""
    band_blurb = {
        "critical": "Strong deception fingerprint across multiple sources.",
        "high": "Multiple deception signals. Pattern is consistent with shadow-fleet behavior.",
        "medium": "Notable anomalies, but signal is not yet decisive.",
        "low": "Behavior consistent with stated identity and route.",
    }[score.band]

    bullets: list[str] = []
    for c in score.components:
        for ev in c.evidence_records:
            if ev.severity in ("critical", "high"):
                bullets.append(f"{ev.title} — {ev.description}")
            if len(bullets) >= 6:
                break
        if len(bullets) >= 6:
            break

    if not bullets:
        bullets.append("No high-severity evidence on file for this vessel.")

    summary = (
        f"{vessel.name} (IMO {vessel.imo}, flag {vessel.flag}) carries a deception "
        f"score of {score.score}/1000 in the {score.band.upper()} band. {band_blurb} "
        f"Owner of record: {vessel.owner.name if vessel.owner else 'unknown'}. "
        f"Recommended action: {score.recommendation}."
    )

    headline = {
        "critical": f"CRITICAL: {vessel.name} matches shadow-fleet deception pattern",
        "high":     f"High-risk deception signals on {vessel.name}",
        "medium":   f"Anomalies on {vessel.name} warrant analyst review",
        "low":      f"{vessel.name} consistent with declared identity",
    }[score.band]

    raw = (
        f"# {headline}\n\n"
        f"{summary}\n\n## Evidence\n"
        + "\n".join(f"- {b}" for b in bullets)
        + f"\n\n**Recommended action:** {score.recommendation}\n"
    )

    return InterdictionBrief(
        vessel_imo=vessel.imo,
        generated_at=datetime.now(timezone.utc),
        headline=headline,
        summary=summary,
        evidence=bullets,
        recommended_action=score.recommendation,
        confidence=min(0.4 + score.score / 1500, 0.95),
        raw_markdown=raw,
    )


def _anthropic_brief(vessel: Vessel, score: RiskScore, settings) -> InterdictionBrief:
    """Real Claude call. Falls back to template on any failure."""
    try:
        import anthropic  # type: ignore[import-not-found]
    except ImportError:
        return _deterministic_brief(vessel, score)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    user_msg = (
        f"Vessel: {vessel.name} (IMO {vessel.imo}, flag {vessel.flag})\n"
        f"Owner: {vessel.owner.name if vessel.owner else 'unknown'}\n"
        f"Score: {score.score}/1000, band {score.band}\n\n"
        f"Evidence package:\n{_build_evidence_block(score)}\n"
    )

    msg = client.messages.create(
        model=settings.llm_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = msg.content[0].text if msg.content else ""

    # Best-effort parse of the structured output.
    headline = ""
    summary = ""
    evidence: list[str] = []
    rec = score.recommendation
    conf = 0.7
    section = None
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("HEADLINE:"):
            headline = s.partition(":")[2].strip()
            section = None
        elif s.startswith("SUMMARY:"):
            summary = s.partition(":")[2].strip()
            section = "summary"
        elif s.startswith("EVIDENCE"):
            section = "evidence"
        elif s.startswith("RECOMMENDED ACTION:"):
            rec = s.partition(":")[2].strip().lower()
            section = None
        elif s.startswith("CONFIDENCE:"):
            try:
                conf = float(s.partition(":")[2].strip())
            except ValueError:
                pass
            section = None
        elif section == "summary" and s:
            summary += " " + s
        elif section == "evidence" and s.startswith("-"):
            evidence.append(s.lstrip("- ").strip())

    return InterdictionBrief(
        vessel_imo=vessel.imo,
        generated_at=datetime.now(timezone.utc),
        headline=headline or f"Brief for {vessel.name}",
        summary=summary.strip() or "(model returned no summary)",
        evidence=evidence,
        recommended_action=rec or score.recommendation,
        confidence=conf,
        raw_markdown=raw,
    )


def generate(db: Session, imo: str) -> InterdictionBrief:
    vessel = db.query(Vessel).filter(Vessel.imo == imo).first()
    if not vessel:
        raise HTTPException(404, f"vessel {imo} not found")

    score = (
        db.query(RiskScore)
        .filter(RiskScore.vessel_imo == imo)
        .order_by(RiskScore.computed_at.desc())
        .first()
    )
    if not score:
        # Score on demand if none exists.
        scoring.score_vessel(db, imo)
        score = (
            db.query(RiskScore)
            .filter(RiskScore.vessel_imo == imo)
            .order_by(RiskScore.computed_at.desc())
            .first()
        )

    settings = get_settings()
    if settings.anthropic_api_key:
        return _anthropic_brief(vessel, score, settings)
    return _deterministic_brief(vessel, score)
