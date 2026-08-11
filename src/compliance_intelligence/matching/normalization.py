from __future__ import annotations

import re
import unicodedata


NON_ALPHANUMERIC = re.compile(r"[^a-z0-9 ]+")
WHITESPACE = re.compile(r"\s+")


def normalize_entity_name(value: str) -> str:
    """Produce a deterministic comparison form without claiming identity equivalence."""

    decomposed = unicodedata.normalize("NFKD", value)
    boundary_preserved = "".join(
        ""
        if unicodedata.category(character).startswith("M")
        else character
        if character.isalnum()
        else " "
        for character in decomposed
    )
    ascii_value = boundary_preserved.encode("ascii", "ignore").decode("ascii").lower()
    cleaned = NON_ALPHANUMERIC.sub(" ", ascii_value)
    return WHITESPACE.sub(" ", cleaned).strip()


def token_sorted(value: str) -> str:
    return " ".join(sorted(normalize_entity_name(value).split()))
