"""NER evaluation over hand-annotated designation excerpts.

Predictions are filtered to the in-scope labels defined in eval/README.md;
matching is exact span + label. Requires the [nlp] extra.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS_PATH = ROOT / "eval" / "data" / "ner_annotations.jsonl"
RESULTS_DIR = ROOT / "eval" / "results"
SCOPE_LABELS = ("PERSON", "ORG", "GPE", "SANCTIONS_PROGRAM", "LEGAL_AUTHORITY", "VESSEL_ID")


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    label: str
    text: str


def _resolve_span(text: str, entity: dict[str, object]) -> Span:
    needle = str(entity["text"])
    occurrence = int(entity.get("occurrence", 1))
    position = -1
    for _ in range(occurrence):
        position = text.find(needle, position + 1)
        if position < 0:
            raise ValueError(f"Annotation {needle!r} occurrence {occurrence} not found")
    return Span(position, position + len(needle), str(entity["label"]), needle)


def load_annotations() -> list[tuple[str, str, list[Span]]]:
    excerpts: list[tuple[str, str, list[Span]]] = []
    with ANNOTATIONS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            text = payload["text"]
            spans = [_resolve_span(text, entity) for entity in payload["entities"]]
            for span in spans:
                if span.label not in SCOPE_LABELS:
                    raise ValueError(f"Out-of-scope label {span.label!r} in annotations")
            excerpts.append((payload["doc_id"], text, spans))
    return excerpts


def _overlaps(left: Span, right: Span) -> bool:
    return left.start < right.end and right.start < left.end


def evaluate() -> dict[str, object]:
    from compliance_intelligence.nlp.extractor import MODEL_NAME, RULES_VERSION, EntityExtractor

    extractor = EntityExtractor()
    excerpts = load_annotations()

    per_label: dict[str, dict[str, int]] = {
        label: {"tp": 0, "fp": 0, "fn": 0} for label in SCOPE_LABELS
    }
    errors = {"boundary": 0, "label": 0, "missed": 0, "spurious": 0}
    error_examples: list[dict[str, object]] = []

    for doc_id, text, gold_spans in excerpts:
        predictions = [
            Span(entity.start, entity.end, entity.label, entity.text)
            for entity in extractor.extract(text)
            if entity.label in SCOPE_LABELS
        ]
        matched_predictions: set[int] = set()
        for gold in gold_spans:
            exact = next(
                (
                    i
                    for i, predicted in enumerate(predictions)
                    if i not in matched_predictions
                    and predicted.start == gold.start
                    and predicted.end == gold.end
                    and predicted.label == gold.label
                ),
                None,
            )
            if exact is not None:
                matched_predictions.add(exact)
                per_label[gold.label]["tp"] += 1
                continue
            per_label[gold.label]["fn"] += 1
            if any(
                _overlaps(predicted, gold) and predicted.label == gold.label
                for predicted in predictions
            ):
                errors["boundary"] += 1
                kind = "boundary"
            elif any(
                predicted.start == gold.start and predicted.end == gold.end
                for predicted in predictions
            ):
                errors["label"] += 1
                kind = "label"
            else:
                errors["missed"] += 1
                kind = "missed"
            if len(error_examples) < 15:
                error_examples.append(
                    {"doc_id": doc_id, "kind": kind, "label": gold.label, "text": gold.text}
                )
        for i, predicted in enumerate(predictions):
            if i not in matched_predictions:
                per_label[predicted.label]["fp"] += 1
                errors["spurious"] += 1

    def metrics(tp: int, fp: int, fn: int) -> dict[str, float]:
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}

    label_metrics = {
        label: {**counts, **metrics(counts["tp"], counts["fp"], counts["fn"])}
        for label, counts in per_label.items()
    }
    total_tp = sum(counts["tp"] for counts in per_label.values())
    total_fp = sum(counts["fp"] for counts in per_label.values())
    total_fn = sum(counts["fn"] for counts in per_label.values())
    macro_labels = [label for label in SCOPE_LABELS if sum(per_label[label].values())]
    macro = {
        metric: round(
            sum(label_metrics[label][metric] for label in macro_labels) / len(macro_labels), 4
        )
        for metric in ("precision", "recall", "f1")
    }

    import spacy

    return {
        "model": MODEL_NAME,
        "spacy_version": spacy.__version__,
        "rules_version": RULES_VERSION,
        "excerpt_count": len(excerpts),
        "gold_span_count": total_tp + total_fn,
        "per_label": label_metrics,
        "micro": metrics(total_tp, total_fp, total_fn),
        "macro": macro,
        "error_taxonomy": errors,
        "error_examples": error_examples,
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# NER evaluation report",
        "",
        f"Generated: {report['generated_at_utc']}",
        f"Model: `{report['model']}` (spaCy {report['spacy_version']}) + `{report['rules_version']}`",
        (
            f"Annotations: `{report['annotations_file']}` "
            f"(sha256 `{str(report['annotations_sha256'])[:12]}…`), "
            f"{report['excerpt_count']} excerpts / {report['gold_span_count']} gold spans. "
            "Single-annotator labels; guidelines in eval/README.md."
        ),
        "",
        "## Per-label metrics (exact span + label match)",
        "",
        "| Label | TP | FP | FN | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|---|",
    ]
    per_label = report["per_label"]
    assert isinstance(per_label, dict)
    for label, counts in per_label.items():
        lines.append(
            f"| {label} | {counts['tp']} | {counts['fp']} | {counts['fn']} | "
            f"{counts['precision']:.3f} | {counts['recall']:.3f} | {counts['f1']:.3f} |"
        )
    micro = report["micro"]
    macro = report["macro"]
    assert isinstance(micro, dict) and isinstance(macro, dict)
    lines += [
        (
            f"| **micro** | | | | {micro['precision']:.3f} | "
            f"{micro['recall']:.3f} | {micro['f1']:.3f} |"
        ),
        (
            f"| **macro** | | | | {macro['precision']:.3f} | "
            f"{macro['recall']:.3f} | {macro['f1']:.3f} |"
        ),
        "",
        f"Error taxonomy: {report['error_taxonomy']}",
        "",
        "## Sample errors",
        "",
    ]
    error_examples = report["error_examples"]
    assert isinstance(error_examples, list)
    for example in error_examples:
        lines.append(
            f"- `{example['doc_id']}` {example['kind']}: {example['label']} {example['text']!r}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    report = evaluate()
    report["generated_at_utc"] = datetime.now(UTC).isoformat()
    report["annotations_file"] = str(ANNOTATIONS_PATH.relative_to(ROOT))
    report["annotations_sha256"] = hashlib.sha256(ANNOTATIONS_PATH.read_bytes()).hexdigest()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "ner_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (RESULTS_DIR / "ner_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"excerpts={report['excerpt_count']} gold_spans={report['gold_span_count']}")
    print(f"micro={report['micro']}")
    print(f"errors={report['error_taxonomy']}")
    print(f"reports={RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
