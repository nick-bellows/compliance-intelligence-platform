from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

# Rule labels are disjoint from the spaCy model's labels, so every extracted
# span is attributable to exactly one origin.
RULES_VERSION = "sanctions-rules-v1"
MODEL_NAME = "en_core_web_sm"
RULE_LABELS = frozenset({"SANCTIONS_PROGRAM", "LEGAL_AUTHORITY", "VESSEL_ID"})

_PROGRAM_CODES = [
    "SDGT",
    "SDNT",
    "SDNTK",
    "IFSR",
    "NPWMD",
    "SDT",
    "FTO",
    "GLOMAG",
    "CAATSA",
    "DPRK",
    "IRGC",
]

_RULER_PATTERNS: list[dict[str, Any]] = (
    [
        {
            "label": "SANCTIONS_PROGRAM",
            "pattern": [{"TEXT": code}],
        }
        for code in _PROGRAM_CODES
    ]
    + [
        {
            "label": "SANCTIONS_PROGRAM",
            "pattern": [{"LOWER": "global"}, {"LOWER": "magnitsky"}],
        },
        {
            "label": "LEGAL_AUTHORITY",
            "pattern": [
                {"LOWER": "executive"},
                {"LOWER": "order"},
                {"TEXT": {"REGEX": r"^\d{5}$"}},
            ],
        },
        {
            "label": "LEGAL_AUTHORITY",
            "pattern": [{"TEXT": "E.O."}, {"TEXT": {"REGEX": r"^\d{5}$"}}],
        },
        {
            "label": "VESSEL_ID",
            "pattern": [{"LOWER": "imo"}, {"TEXT": {"REGEX": r"^\d{7}$"}}],
        },
    ]
)


@dataclass(frozen=True, slots=True)
class ExtractedEntity:
    text: str
    label: str
    start: int
    end: int
    rule_or_model: str


class EntityExtractor:
    """spaCy NER plus versioned domain rules; requires the [nlp] extra."""

    def __init__(self) -> None:
        self._nlp: Any = None

    def _pipeline(self) -> Any:
        if self._nlp is None:
            try:
                import spacy
            except ImportError as error:
                raise RuntimeError(
                    'Entity extraction requires the [nlp] extra: pip install -e ".[nlp]"'
                ) from error
            nlp = spacy.load(MODEL_NAME)
            ruler = cast(Any, nlp.add_pipe("entity_ruler", before="ner"))
            ruler.add_patterns(_RULER_PATTERNS)
            self._nlp = nlp
        return self._nlp

    def extract(self, text: str) -> tuple[ExtractedEntity, ...]:
        document = self._pipeline()(text)
        return tuple(
            ExtractedEntity(
                text=entity.text,
                label=entity.label_,
                start=entity.start_char,
                end=entity.end_char,
                rule_or_model=(
                    f"rule:{RULES_VERSION}"
                    if entity.label_ in RULE_LABELS
                    else f"model:{MODEL_NAME}"
                ),
            )
            for entity in document.ents
        )
