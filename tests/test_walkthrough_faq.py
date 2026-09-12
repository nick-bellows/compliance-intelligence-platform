"""The recruiter FAQ on the committed walkthrough must rest on committed evidence.

The build script reads its figures from ``eval/results`` and ``--check`` keeps
the page current, so these tests guard the other half: that the committed page
carries the section at all, that every link into the repository resolves to a
tracked file, and that the figures on the page are the figures in the reports
rather than a stale copy of them.
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs" / "index.html"
RESULTS = ROOT / "eval" / "results"
sys.path.insert(0, str(ROOT / "scripts"))

from build_portfolio_walkthrough import faq_figures, portfolio_faq


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"] or "")
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")


def _faq_markup() -> str:
    markup = SITE.read_text(encoding="utf-8")
    start = markup.index('<section id="faq"')
    return markup[start : markup.index("</section>", start)]


def test_committed_page_carries_the_faq_the_builder_produces() -> None:
    assert portfolio_faq().strip() in SITE.read_text(encoding="utf-8")
    parser = _Links()
    parser.feed(SITE.read_text(encoding="utf-8"))
    assert {"reviewer-tour", "review-queue", "faq"} <= parser.ids


def test_every_faq_entry_is_a_question_with_an_answer() -> None:
    faq = _faq_markup()
    assert faq.count("<details>") >= 10
    assert faq.count("<details>") == faq.count("<summary>") == faq.count("</details>")
    for question in re.findall(r"<summary>(.*?)</summary>", faq):
        assert question.endswith("?"), question


def test_faq_links_resolve_to_tracked_files() -> None:
    parser = _Links()
    parser.feed(_faq_markup())
    prefix = "https://github.com/nick-bellows/compliance-intelligence-platform/blob/master/"
    repo_links = [link for link in parser.links if link.startswith(prefix)]
    assert repo_links
    for link in repo_links:
        parts = urlparse(link).path.strip("/").split("/")
        assert ROOT.joinpath(*parts[4:]).is_file(), link
    required = ("docs/limitations.md", "docs/threat-model.md", "ROADMAP.md", "tests/test_api.py")
    for path in required:
        assert any(link.endswith("/" + path) for link in repo_links), path


def test_faq_figures_match_the_committed_reports() -> None:
    """Belt and braces: the builder read these, and the page still shows them."""
    faq = _faq_markup()
    matching = json.loads((RESULTS / "matching_report.json").read_text(encoding="utf-8"))
    holdout = matching["scorers"]["rapidfuzz"]["holdout_at_recommended"]
    ner = json.loads((RESULTS / "ner_report.json").read_text(encoding="utf-8"))
    retrieval = json.loads((RESULTS / "retrieval_report.json").read_text(encoding="utf-8"))

    assert f"precision is {holdout['precision']:.3f}" in faq
    assert f"recall {holdout['recall']:.3f}" in faq
    assert f"F1 {holdout['f1']:.3f}" in faq
    assert f"of the {holdout['false_negatives']} misses" in faq
    assert f"micro F1 of {ner['micro']['f1']:.3f}" in faq
    assert f"{ner['per_label']['PERSON']['f1']:.3f} on PERSON" in faq
    assert f"Recall@10 {retrieval['aggregate']['dense']['recall@10']:.3f}" in faq
    assert f"MRR ({retrieval['aggregate']['hybrid']['mrr']:.3f}" in faq
    hybrid, bm25 = retrieval['aggregate']['hybrid'], retrieval['aggregate']['bm25']
    assert hybrid['mrr'] > bm25['mrr'] and hybrid['recall@10'] < bm25['recall@10'], (
        'the FAQ says hybrid edges BM25 on MRR and trails it at Recall@10'
    )

    figures = faq_figures()
    for value in figures.values():
        assert value in faq, value
