"""Interdiction-brief generator — packages evidence and asks Claude for a writeup."""

from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas import InterdictionBrief

# Lazy import of anthropic so missing key doesn't crash app startup.
SYSTEM_PROMPT = """\
You are an intelligence analyst writing a maritime deception interdiction brief
for a coalition naval task force. Be specific, evidence-grounded, and concise.
Output sections: Headline, Summary, Evidence (bulleted), Recommended Action,
Confidence (0-1).
"""


def generate(db: Session, imo: str) -> InterdictionBrief:
    """Build the evidence package for a vessel and call Claude for the brief.

    Implementation outline (fill in later):
      1. Load vessel, score, components, ownership graph, recent events.
      2. Render structured-evidence prompt for Claude.
      3. Call anthropic.Anthropic().messages.create with model from settings.
      4. Parse model output into InterdictionBrief sections.
    """
    _settings = get_settings()  # noqa: F841 — used once API call is wired
    raise NotImplementedError("brief_generator.generate not implemented yet")
