"""Generate the labeled name-pair set for matching evaluation.

All names are fictional. Positive pairs are produced by surface transformations
(typos, diacritics, legal suffixes, token reordering, abbreviation) that are
independent of any scorer under test, avoiding circular tuning. Hard negatives
and ambiguous near-neighbors are hand-written. Labels encode the desired
screening behavior: expected_match=true means a reviewer should see this pair
flagged as a review lead. Generated output is manually reviewed before commit;
single-annotator review is a documented limitation.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 20260810
OUTPUT = Path(__file__).resolve().parents[1] / "eval" / "data" / "matching_cases.csv"
TUNE_FRACTION = 0.6

ORGANIZATIONS = [
    "Acme Galactic Holdings",
    "Contoso Maritime Group",
    "Fabrikam Industrial Works",
    "Northwind Shipping Company",
    "Globex Petroleum Trading",
    "Initech Financial Services",
    "Umbrella Logistics Partners",
    "Stark Metallurgy Group",
    "Wayne Chemical Industries",
    "Tyrell Agritech Corporation",
    "Wonka Confectionery Exports",
    "Sirius Cybernetics Group",
    "Vandelay Import Export",
    "Prestige Worldwide Freight",
    "Duff Beverage Distribution",
    "Oscorp Materials Research",
    "Cyberdyne Precision Systems",
    "Aperture Optics Laboratories",
    "Black Mesa Transit Authority",
    "Hooli Data Holdings",
    "Pied Piper Compression Labs",
    "Massive Dynamic Ventures",
    "Veridian Dynamics Group",
    "Soylent Nutrition Corporation",
    "Gringotts Bullion Reserve",
    "Weyland Mining Consortium",
    "Zorin Industries International",
    "Krusty Brand Merchandising",
    "Planet Express Cargo",
    "Monarch Aeronautics Group",
]

PERSONS = [
    "Jonathan Q Testman",
    "Maria Ficticia Delgado",
    "Viktor Primerov",
    "Amina Misalova",
    "Chen Jiawei Example",
    "Olusegun Sampleton",
    "Ingrid Falskesen",
    "Rashid Al Mithali",
    "Petra Novakova Vzorek",
    "Diego Ejemplar Santos",
]

LEGAL_SUFFIXES = ["LLC", "Ltd", "Inc", "GmbH", "S.A.", "Corporation", "Co", "Group"]
SUFFIX_TOKENS = {suffix.lower().strip(".") for suffix in LEGAL_SUFFIXES} | {
    "company",
    "corporation",
    "group",
    "partners",
    "consortium",
    "ventures",
}

DIACRITICS = {
    "a": "á",
    "e": "é",
    "i": "í",
    "o": "ó",
    "u": "ü",
    "c": "ç",
    "n": "ñ",
    "s": "š",
    "z": "ž",
}

# Distinct fictional entities sharing generic tokens; screening should NOT flag these.
HARD_NEGATIVES = [
    ("Acme Galactic Holdings", "Zenith Galactic Partners"),
    ("Contoso Maritime Group", "Fabrikam Maritime Group"),
    ("Northwind Shipping Company", "Southgale Shipping Company"),
    ("Globex Petroleum Trading", "Meridian Petroleum Trading"),
    ("Initech Financial Services", "Veridian Financial Services"),
    ("Umbrella Logistics Partners", "Parasol Freight Partners"),
    ("Stark Metallurgy Group", "Sterner Alloy Group"),
    ("Wayne Chemical Industries", "Grayson Chemical Industries"),
    ("Tyrell Agritech Corporation", "Rosen Agritech Corporation"),
    ("Wonka Confectionery Exports", "Slugworth Confectionery Exports"),
    ("Sirius Cybernetics Group", "Polaris Cybernetics Group"),
    ("Vandelay Import Export", "Pennypacker Import Export"),
    ("Prestige Worldwide Freight", "Prestige Interplanetary Catering"),
    ("Duff Beverage Distribution", "Fudd Beverage Distribution"),
    ("Oscorp Materials Research", "Roxxon Materials Research"),
    ("Cyberdyne Precision Systems", "Omni Precision Systems"),
    ("Aperture Optics Laboratories", "Aperture Marine Salvage"),
    ("Black Mesa Transit Authority", "White Butte Transit Authority"),
    ("Hooli Data Holdings", "Endframe Data Holdings"),
    ("Massive Dynamic Ventures", "Colossal Static Ventures"),
    ("Jonathan Q Testman", "Jonathan Q Bencher"),
    ("Maria Ficticia Delgado", "Lucia Ficticia Delgado"),
    ("Viktor Primerov", "Viktor Obraztsov"),
    ("Chen Jiawei Example", "Chen Zhihao Example"),
    ("Rashid Al Mithali", "Tariq Al Mithali"),
]

# Boundary cases labeled individually; notes explain the judgment.
AMBIGUOUS = [
    ("Acme Galactic Holdings", "Acme Galactic Holdings BV", True, "foreign-suffix variant, plausibly the same entity"),
    ("Planet Express Cargo", "Planet Express Cartage", True, "near-synonym token, plausibly the same entity"),
    ("Monarch Aeronautics Group", "Monarch Aquatics Group", False, "different industry despite shared brand token"),
    ("Duff Beverage Distribution", "Duff Beverage Distributors", True, "inflection of the same trading name"),
    ("Hooli Data Holdings", "Hooli Cloud Holdings", False, "different line of business under a shared brand"),
    ("Krusty Brand Merchandising", "Krusty Brand Merchandise", True, "inflection of the same trading name"),
    ("Veridian Dynamics Group", "Viridian Dynamics Group", True, "single-letter spelling variant of the same name"),
    ("Weyland Mining Consortium", "Weyland Mining Corp", True, "suffix variant of the same name"),
    ("Gringotts Bullion Reserve", "Gringotts Bullion Exchange", False, "different institution type sharing a brand"),
    ("Soylent Nutrition Corporation", "Soylent Nutrition Cooperative", False, "different legal form suggests a distinct entity"),
    ("Ingrid Falskesen", "Ingrid Falskesdottir", False, "different patronymic surname"),
    ("Petra Novakova Vzorek", "Petra Novak Vzorek", True, "surname inflection variant of the same person"),
    ("Diego Ejemplar Santos", "Diego Ejemplar-Santos", True, "hyphenation variant of the same person"),
    ("Amina Misalova", "Amina Misalov", True, "gendered surname inflection of the same person"),
    ("Olusegun Sampleton", "Olusegun Sampson", False, "different surname beyond spelling variation"),
]


def _swap_suffix(name: str, rng: random.Random) -> tuple[str, str]:
    tokens = name.split()
    if tokens[-1].lower().strip(".") in SUFFIX_TOKENS:
        replacement = rng.choice([s for s in LEGAL_SUFFIXES if s.lower() != tokens[-1].lower()])
        return " ".join([*tokens[:-1], replacement]), f"suffix swap: {tokens[-1]} -> {replacement}"
    suffix = rng.choice(LEGAL_SUFFIXES)
    return f"{name} {suffix}", f"suffix added: {suffix}"


def _reorder(name: str, rng: random.Random) -> tuple[str, str]:
    tokens = name.split()
    shuffled = tokens[:]
    while shuffled == tokens:
        rng.shuffle(shuffled)
    return " ".join(shuffled), "token reorder"


def _misspell(name: str, rng: random.Random) -> tuple[str, str]:
    tokens = name.split()
    candidates = [i for i, token in enumerate(tokens) if len(token) > 3]
    index = rng.choice(candidates)
    token = tokens[index]
    position = rng.randrange(1, len(token) - 1)
    operation = rng.choice(("transpose", "drop", "double"))
    if operation == "transpose":
        token = token[: position - 1] + token[position] + token[position - 1] + token[position + 1 :]
    elif operation == "drop":
        token = token[:position] + token[position + 1 :]
    else:
        token = token[:position] + token[position] + token[position:]
    tokens[index] = token
    return " ".join(tokens), f"misspelling ({operation})"


def _transliterate(name: str, rng: random.Random) -> tuple[str, str]:
    characters = list(name)
    positions = [i for i, ch in enumerate(characters) if ch.lower() in DIACRITICS]
    chosen = rng.sample(positions, min(len(positions), rng.randint(1, 3)))
    for i in chosen:
        replacement = DIACRITICS[characters[i].lower()]
        characters[i] = replacement.upper() if characters[i].isupper() else replacement
    return "".join(characters), "diacritic variant"


def _alias(name: str, rng: random.Random) -> tuple[str, str]:
    tokens = name.split()
    if rng.random() < 0.5 and len(tokens) >= 3:
        initials = "".join(token[0].upper() for token in tokens[:-1])
        return f"{initials} {tokens[-1]}", "abbreviation alias"
    index = rng.randrange(1, len(tokens) - 1) if len(tokens) > 2 else 0
    reduced = tokens[:index] + tokens[index + 1 :]
    return " ".join(reduced), "token-drop alias"


ORG_TRANSFORMS = {
    "legal_suffix": _swap_suffix,
    "token_reorder": _reorder,
    "misspelling": _misspell,
    "transliteration": _transliterate,
    "alias": _alias,
}

PERSON_TRANSFORMS = {
    "misspelling": _misspell,
    "transliteration": _transliterate,
    "token_reorder": _reorder,
}


def generate_cases() -> list[dict[str, str]]:
    rng = random.Random(SEED)
    cases: list[dict[str, str]] = []

    def add(query: str, candidate: str, expected: bool, case_type: str, notes: str) -> None:
        cases.append(
            {
                "case_id": f"{case_type}-{sum(1 for c in cases if c['case_type'] == case_type) + 1:03d}",
                "query_name": query,
                "candidate_name": candidate,
                "expected_match": "true" if expected else "false",
                "case_type": case_type,
                "notes": notes,
            }
        )

    for index, name in enumerate(ORGANIZATIONS):
        if index % 3 == 0:
            add(name, name, True, "exact", "identical strings")
        for case_type in rng.sample(sorted(ORG_TRANSFORMS), 3):
            variant, note = ORG_TRANSFORMS[case_type](name, rng)
            add(name, variant, True, case_type, note)

    for index, name in enumerate(PERSONS):
        if index % 4 == 0:
            add(name, name, True, "exact", "identical strings")
        for case_type in rng.sample(sorted(PERSON_TRANSFORMS), 2):
            variant, note = PERSON_TRANSFORMS[case_type](name, rng)
            add(name, variant, True, case_type, note)

    for left, right in HARD_NEGATIVES:
        add(left, right, False, "hard_negative", "distinct entities sharing generic tokens")

    for left, right, expected, note in AMBIGUOUS:
        add(left, right, expected, "ambiguous_near_neighbor", note)

    split_rng = random.Random(SEED + 1)
    by_type: dict[str, list[dict[str, str]]] = {}
    for case in cases:
        by_type.setdefault(case["case_type"], []).append(case)
    for grouped in by_type.values():
        split_rng.shuffle(grouped)
        tune_count = round(len(grouped) * TUNE_FRACTION)
        for position, case in enumerate(grouped):
            case["split"] = "tune" if position < tune_count else "holdout"

    cases.sort(key=lambda case: case["case_id"])
    return cases


def main() -> int:
    cases = generate_cases()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "case_id",
                "query_name",
                "candidate_name",
                "expected_match",
                "case_type",
                "split",
                "notes",
            ),
        )
        writer.writeheader()
        writer.writerows(cases)
    print(f"wrote {len(cases)} cases to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
