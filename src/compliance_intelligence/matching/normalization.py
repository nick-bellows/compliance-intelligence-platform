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


# Alpha-2 forms for country names appearing in sanctions-list data and common
# query spellings. Unmapped values fall back to their normalized name, so overlap
# detection still works when both sides use the same wording.
_COUNTRY_ALPHA2 = {
    "afghanistan": "AF",
    "belarus": "BY",
    "burma": "MM",
    "central african republic": "CF",
    "china": "CN",
    "congo democratic republic of the": "CD",
    "congo the democratic republic of the": "CD",
    "cote d ivoire": "CI",
    "cuba": "CU",
    "democratic peoples republic of korea": "KP",
    "democratic republic of the congo": "CD",
    "dprk": "KP",
    "eritrea": "ER",
    "ethiopia": "ET",
    "germany": "DE",
    "great britain": "GB",
    "guinea": "GN",
    "guinea bissau": "GW",
    "haiti": "HT",
    "iran": "IR",
    "iran islamic republic of": "IR",
    "iraq": "IQ",
    "japan": "JP",
    "korea democratic peoples republic of": "KP",
    "korea north": "KP",
    "lebanon": "LB",
    "libya": "LY",
    "mali": "ML",
    "mexico": "MX",
    "myanmar": "MM",
    "nicaragua": "NI",
    "north korea": "KP",
    "pakistan": "PK",
    "panama": "PA",
    "russia": "RU",
    "russian federation": "RU",
    "serbia": "RS",
    "somalia": "SO",
    "south sudan": "SS",
    "spain": "ES",
    "sudan": "SD",
    "switzerland": "CH",
    "syria": "SY",
    "syrian arab republic": "SY",
    "turkey": "TR",
    "turkiye": "TR",
    "uk": "GB",
    "ukraine": "UA",
    "united arab emirates": "AE",
    "united kingdom": "GB",
    "united kingdom of great britain and northern ireland": "GB",
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "venezuela": "VE",
    "venezuela bolivarian republic of": "VE",
    "yemen": "YE",
    "zimbabwe": "ZW",
}


_APOSTROPHES = ("'", "’", "ʼ")


def normalize_country(value: str) -> str:
    """Map a country name or code to alpha-2 where known, else its normalized form.

    Apostrophes are removed rather than turned into token boundaries so that
    "Democratic People's Republic of Korea" (the UN spelling) reaches its map key.
    Known aliases such as "UK"/"USA" are mapped before the generic two-letter rule.
    """

    stripped = value
    for apostrophe in _APOSTROPHES:
        stripped = stripped.replace(apostrophe, "")
    normalized = normalize_entity_name(stripped)
    mapped = _COUNTRY_ALPHA2.get(normalized)
    if mapped is not None:
        return mapped
    if len(normalized) == 2 and normalized.isalpha():
        return normalized.upper()
    return normalized
