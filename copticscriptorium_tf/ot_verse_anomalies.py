"""Source-literal OT verse-anomaly batch evidence, with cautious LXX address probes.

Retains *only* anomalous marker metadata; no Coptic text, translations, lexical
forms or Greek words. Address existence is not bilingual textual equivalence.
"""
from __future__ import annotations

from collections import Counter
import re
from typing import Callable

from .parser import TAG_RE

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
_HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_VERSE = re.compile(r'(?:^|\s)verse_n\s*=\s*"([^"]*)"')
_CHAPTER = re.compile(r'(?:^|\s)chapter_n\s*=\s*"([^"]*)"')
MAX_EXPLICIT_MISSING = 256


def _positive(value: str | None) -> int | None:
    if value is None or not value.isascii() or not value.isdecimal():
        return None
    number = int(value)
    return number if number > 0 else None


def _invalid_literal_class(value: str | None) -> str | None:
    """Classify source *syntax*, not a conjectural biblical verse number."""
    if value is None:
        return "missing_attribute"
    if value == "":
        return "empty_literal"
    if value.isascii() and value.isdecimal():
        return "zero_literal" if int(value) == 0 else None
    if re.fullmatch(r"-[0-9]+", value):
        return "signed_nonpositive_literal"
    return "nondecimal_literal"


class CopticOtVerseAnomalyBatch:
    """Collect every exceptional OT marker occurrence, not just sample records."""

    def __init__(self, *, source_commit: str) -> None:
        if source_commit != COPTIC_PIN:
            raise ValueError("unsupported source commit for Coptic OT anomaly report")
        self.source_commit = source_commit
        self._cases: list[dict[str, object]] = []
        self._counts: Counter[str] = Counter()
        self._records: set[str] = set()
        self._scanned_ot_records = 0
        self._greek_checked = False

    def add(
        self, source_text: str, source_record_id: str, *,
        source_sha256: str, scope: str, corpus: str,
        cts_work: str | None, chapter: str | None,
        edition: str | None, lxx_book: str | None = None,
    ) -> None:
        if not isinstance(source_text, str) or not source_record_id:
            raise ValueError("missing source text or physical record ID for event positions")
        if not isinstance(source_sha256, str) or _HEX_SHA256.fullmatch(source_sha256) is None:
            raise ValueError("source SHA256 must identify exact source TT bytes")
        if source_record_id.casefold() in self._records:
            raise ValueError(f"duplicate source record anomaly scan: {source_record_id}")
        if self._greek_checked:
            raise ValueError("cannot add source records after Greek crosscheck")
        self._records.add(source_record_id.casefold())
        if scope != "ot_candidate":
            return
        self._scanned_ot_records += 1

        previous: int | None = None
        current_chapter = chapter
        embedded_chapter = None
        word_starts = 0
        verse_tag_ordinal = 0
        for tag in TAG_RE.finditer(source_text):
            closing, name, attributes = tag.group(1), tag.group(2), tag.group(3)
            if closing:
                continue
            if name == "norm":
                word_starts += 1
                continue
            if name == "chapter_n":
                match = _CHAPTER.search(attributes)
                next_chapter = match.group(1) if match else None
                if next_chapter != embedded_chapter:
                    previous = None
                    embedded_chapter = next_chapter
                    current_chapter = next_chapter
                continue
            if name != "verse_n":
                continue

            verse_tag_ordinal += 1
            match = _VERSE.search(attributes)
            literal = match.group(1) if match else None
            if literal is not None and len(literal) > 256:
                raise ValueError("source verse literal exceeds bounded anomaly schema")
            current = _positive(literal)
            kind = None
            if current is None:
                kind = "missing_or_nonpositive_literal"
            elif previous is not None and current > previous + 1:
                kind = "gapped"

            if kind:
                missing_count = (
                    current - previous - 1
                    if kind == "gapped" and current is not None and previous is not None
                    else 0
                )
                missing = (
                    list(range(previous + 1, current))
                    if kind == "gapped" and missing_count <= MAX_EXPLICIT_MISSING
                    else []
                )
                self._cases.append({
                    "kind": kind,
                    "source_record_id": source_record_id,
                    "source_sha256": source_sha256,
                    "source_corpus": corpus,
                    "source_cts_work": cts_work,
                    "source_edition": edition,
                    "source_chapter": current_chapter,
                    "source_marker_ordinal": verse_tag_ordinal,
                    "source_tag_offset": tag.start(),
                    "source_word_starts_before": word_starts,
                    "literal": literal,
                    "invalid_literal_class": (
                        _invalid_literal_class(literal)
                        if kind == "missing_or_nonpositive_literal" else None
                    ),
                    "previous_verse": previous,
                    "current_verse": current,
                    "missing_count": missing_count,
                    "missing_verse_numbers": missing,
                    "lxx_book": lxx_book,
                    "greek_status": "not_checked",
                    "greek_missing_intermediate": [],
                    "interpretation": "Greek reference existence only, not textual equivalence",
                })
                self._counts[kind] += 1
            previous = current

    def inspect_greek(
        self, *,
        verse_lookup: Callable[[str, int, int], int | None],
        subverse_lookup: Callable[[int], tuple[str, ...] | list[str]],
    ) -> None:
        if self._greek_checked:
            raise ValueError("Greek crosscheck has already run")
        self._greek_checked = True
        # Only *missing intermediate* Greek addresses are investigated here.
        # Invalid source markers have no knowable target reference.
        for case in self._cases:
            if case["kind"] != "gapped":
                case["greek_status"] = "not_inferable"
                continue
            chapter = _positive(case["source_chapter"])
            book = case["lxx_book"]
            if not isinstance(book, str) or not book or chapter is None:
                case["greek_status"] = "source_reference_unclassified"
                continue
            if case["missing_count"] > MAX_EXPLICIT_MISSING:
                case["greek_status"] = "gap_too_large_for_automatic_crosscheck"
                continue
            results: list[dict[str, object]] = []
            for verse in case["missing_verse_numbers"]:
                node = verse_lookup(book, chapter, verse)
                if node is not None:
                    if not isinstance(node, int) or isinstance(node, bool) or node < 1:
                        raise ValueError("Greek verse provider returned invalid node ID")
                    distinct_subverses = tuple(dict.fromkeys(subverse_lookup(node)))
                    results.append({
                        "verse": verse, "address": "present",
                        "subverse_count": len(distinct_subverses),
                    })
                else:
                    results.append({
                        "verse": verse, "address": "absent", "subverse_count": 0,
                    })
            case["greek_missing_intermediate"] = results
            case["greek_status"] = "crosschecked_address_only"

    def report(self) -> dict[str, object]:
        cases = sorted(
            self._cases,
            key=lambda x: (
                str(x["source_record_id"]).casefold(),
                int(x["source_marker_ordinal"]),
            ),
        )
        groups: Counter[str] = Counter()
        invalid_classes: Counter[str] = Counter()
        for case in cases:
            if case["kind"] == "missing_or_nonpositive_literal":
                kind = case["invalid_literal_class"]
                if not isinstance(kind, str):
                    raise ValueError("invalid verse literal has no source-literal class")
                invalid_classes[kind] += 1
            group = "|".join((
                str(case["source_cts_work"] or "<unknown>"),
                str(case["source_edition"] or "<unknown>"),
                str(case["kind"]),
            ))
            groups[group] += 1
        return {
            "schema": "coptic_ot_source_verse_anomalies_v1",
            "source_commit": self.source_commit,
            "scanned_ot_records": self._scanned_ot_records,
            "counts": dict(sorted(self._counts.items())),
            "invalid_literal_classes": dict(sorted(invalid_classes.items())),
            "by_work_edition_kind": dict(sorted(groups.items())),
            "cases": cases,
            "warning": (
                "literal source marker anomalies and Greek verse/subverse address lookups only; "
                "no inferred lost Coptic text or Greek-Coptic word correspondence"
            ),
        }
