import pytest

pytest.importorskip("spacy")

from compliance_intelligence.nlp.extractor import EntityExtractor

TEXT = (
    "OFAC designated Jonathan Q Testman under Executive Order 13224 as an SDGT. "
    "The vessel FORTUNE STAR (IMO 9999999) was identified as blocked property in Panama."
)


@pytest.mark.requires_models
def test_extractor_attributes_rules_and_model() -> None:
    entities = EntityExtractor().extract(TEXT)
    by_label = {}
    for entity in entities:
        by_label.setdefault(entity.label, []).append(entity)

    authorities = by_label.get("LEGAL_AUTHORITY", [])
    assert any(entity.text == "Executive Order 13224" for entity in authorities)
    assert all(entity.rule_or_model.startswith("rule:") for entity in authorities)

    programs = by_label.get("SANCTIONS_PROGRAM", [])
    assert any(entity.text == "SDGT" for entity in programs)

    vessels = by_label.get("VESSEL_ID", [])
    assert any("9999999" in entity.text for entity in vessels)

    model_entities = [e for e in entities if e.rule_or_model.startswith("model:")]
    assert model_entities

    for entity in entities:
        assert TEXT[entity.start : entity.end] == entity.text
