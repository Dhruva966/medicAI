"""OFAC Specially Designated Nationals (SDN) list — public, no auth.

Docs: https://ofac.treasury.gov/specially-designated-nationals-and-blocked-persons-list-sdn-human-readable-lists
"""

from typing import Any


def load_sdn_list() -> list[dict[str, Any]]:
    """Download and parse the SDN list. Cache locally; refresh daily."""
    raise NotImplementedError("ofac.load_sdn_list not implemented yet")


def is_sanctioned_vessel(imo: str) -> bool:
    """Lookup whether a vessel IMO appears in the SDN list."""
    raise NotImplementedError("ofac.is_sanctioned_vessel not implemented yet")


def is_sanctioned_owner(name: str) -> bool:
    """Lookup whether an owner/company name appears in the SDN list."""
    raise NotImplementedError("ofac.is_sanctioned_owner not implemented yet")
