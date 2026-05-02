"""Equasis — vessel ownership and flag history.

No public API; uses a session cookie scraped from a manual login.
Treat carefully: cache aggressively, do not hammer the site.
"""

from typing import Any


def get_owner_chain(imo: str) -> list[dict[str, Any]]:
    """Return the ownership chain for a vessel: registered owner → ISM manager → beneficial owner."""
    raise NotImplementedError("equasis.get_owner_chain not implemented yet")


def get_flag_history(imo: str) -> list[dict[str, Any]]:
    """Return flag-state history for a vessel."""
    raise NotImplementedError("equasis.get_flag_history not implemented yet")
