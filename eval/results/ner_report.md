# NER evaluation report

Generated: 2026-08-11T02:54:47.487766+00:00
Model: `en_core_web_sm` (spaCy 3.8.15) + `sanctions-rules-v1`
Annotations: `eval\data\ner_annotations.jsonl` (sha256 `1d2a7627cf68…`), 22 excerpts / 236 gold spans. Single-annotator labels; guidelines in eval/README.md.

## Per-label metrics (exact span + label match)

| Label | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 0 | 64 | 44 | 0.000 | 0.000 | 0.000 |
| ORG | 3 | 66 | 23 | 0.043 | 0.115 | 0.063 |
| GPE | 97 | 10 | 16 | 0.906 | 0.858 | 0.882 |
| SANCTIONS_PROGRAM | 11 | 1 | 15 | 0.917 | 0.423 | 0.579 |
| LEGAL_AUTHORITY | 25 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| VESSEL_ID | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| **micro** | | | | 0.495 | 0.585 | 0.536 |
| **macro** | | | | 0.644 | 0.566 | 0.587 |

Error taxonomy: {'boundary': 31, 'label': 10, 'missed': 57, 'spurious': 141}

## Sample errors

- `2026-16153` boundary: PERSON 'AL-SHABBANI, Basheer Abdulkadhim Alwan'
- `2026-16153` boundary: PERSON 'AL-SHABANI, Bashir Abd al Kazim Alwan'
- `2026-16153` missed: PERSON 'ALSHABBANI, Basheer'
- `2026-16153` missed: PERSON 'SHABBAN, Basheer'
- `2026-15996` boundary: PERSON 'ACOSTA HERNANDEZ, Regulo'
- `2026-15996` boundary: PERSON 'ACOSTA HERNANDEZ, Regulo Gilberto'
- `2026-15996` missed: PERSON 'Tobolio'
- `2026-15996` label: GPE 'Sinaloa'
- `2026-15996` label: GPE 'Sinaloa'
- `2026-15996` missed: SANCTIONS_PROGRAM 'ILLICIT-DRUGS-EO14059'
- `2026-15785` missed: PERSON 'DURANSOY, Cagri'
- `2026-15157` boundary: PERSON 'ALVARADO RODRIGUEZ, Martha Alicia'
- `2026-15157` missed: SANCTIONS_PROGRAM 'ILLICIT-DRUGS-EO14059'
- `2026-15157` missed: ORG 'CARTEL DE JALISCO NUEVA GENERACION'
- `2026-14247` boundary: PERSON 'RASHEVSKYI, Dmytro'
