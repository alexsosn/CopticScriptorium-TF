"""Exact TT verse-zero *source-span* topology of Bohairic Psalm witnesses (#199).

No Greek verse-zero, superscription, bilingual translation or word correspondence
is inferred. A zero-labeled TT source event may contain zero or more Coptic
words. Keep raw event and source-verse labels unchanged in native Text-Fabric.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import re
from typing import Any, Callable

from .model import DocumentModel
from .parser import TAG_RE, ATTR_RE

SOURCE_PIN = "6fb51458e7156dd5387c2b2dca207aac1692e4d0"
_SOURCE_RECORD = re.compile(r"bohairic\.ot/bohairic\.ot:19_Psalmi_(\d{3})\Z")
_SOURCE_CTS = re.compile(r"urn:cts:copticLit:ot\.pss\.bohairic_ed:(\d+)\Z")
_SHA256 = re.compile("[0-9a-f]{64}\\Z")
SCHEMA = "coptic_bohairic_psalm_zero_span_evidence_v1"


def _positive_literal(value: object) -> int | None:
    if (
        isinstance(value, str) and value.isascii() and value.isdecimal()
        and int(value) > 0
    ):
        return int(value)
    return None


def _original_verse_literal(attrs: str) -> str | None:
    # Only original raw `verse_n` tag attributes, never reconstruction from
    # a title or arbitrary generic verse string. Malformed duplicates fail.
    hits = [
        match.group(2) for match in ATTR_RE.finditer(attrs)
        if match.group(1) == "verse_n"
    ]
    if len(hits) != 1:
        raise ValueError("missing or duplicated source verse_n attribute")
    return hits[0]


def inspect_psalm_zero(
    document: DocumentModel,
    *,
    greek_verse: Callable[[int, int], int | None] | None = None,
    greek_subverse: Callable[[int], tuple[object, ...]] | None = None,
) -> dict[str, object] | None:
    """Inspect first zero-labeled source span for one exact Bohairic Psalm.

    Strict source bounds require Coptic repository and commit, physical
    record chapter/CTS/edition, and raw TT SHA256. Non-Psalms return None.
    In particular the two Bohairic Lamentations verse-zero events are not
    misidentified as Psalm titles.
    """
    cts = document.metadata.get("document_cts_urn", "")
    is_psalm = (
        document.corpus == "bohairic.ot"
        and (document.source_record_id.startswith("bohairic.ot/bohairic.ot:19_Psalmi_")
             or cts.startswith("urn:cts:copticLit:ot.pss."))
    )
    if not is_psalm:
        return None

    record = _SOURCE_RECORD.fullmatch(document.source_record_id)
    cts_match = _SOURCE_CTS.fullmatch(cts)
    chapter = _positive_literal(document.metadata.get("chapter"))
    if (
        record is None or cts_match is None or chapter is None
        or chapter > 151
        or int(record[1]) != chapter
        or int(cts_match[1]) != chapter
        or document.dataset != "bohairic.ot"
    ):
        raise ValueError("Psalm source record, chapter, CTS work or edition mismatch")
    if (
        document.upstream_repository != "CopticScriptorium/corpora"
        or document.upstream_commit != SOURCE_PIN
        or not isinstance(document.source_sha256, str)
        or _SHA256.fullmatch(document.source_sha256) is None
        or sha256(document.source_text.encode("utf-8")).hexdigest()
        != document.source_sha256
    ):
        raise ValueError("Psalm source revision or original TT sha256 mismatch")

    boundaries: list[tuple[int, int, str, int]] = []
    norms: list[int] = []
    for tag in TAG_RE.finditer(document.source_text):
        closing, name, attrs = tag.group(1), tag.group(2), tag.group(3)
        if closing:
            continue
        if name == "norm":
            norms.append(tag.start())
        elif name == "verse_n":
            boundaries.append((
                tag.start(), tag.end(), _original_verse_literal(attrs), len(norms)
            ))

    zero = [boundary for boundary in boundaries if boundary[2] == "0"]
    if len(zero) != 1:
        raise ValueError("Psalm source must have exactly one original zero verse marker")
    if boundaries[0] != zero[0] or zero[0][3] != 0:
        raise ValueError("Psalm zero must be first original source verse marker before words")

    start, end, literal, prior_words = zero[0]
    next_boundary = boundaries[1] if len(boundaries) > 1 else None
    next_literal: str | None = next_boundary[2] if next_boundary else None
    raw_word_count = (
        sum(end <= p < next_boundary[0] for p in norms)
        if next_boundary else sum(p >= end for p in norms)
    )
    parsed_word_count = sum(word.verse_n == "0" for word in document.words)
    if parsed_word_count != raw_word_count:
        raise ValueError("Psalm zero source tokens disagree with parsed Coptic word labels")

    if next_boundary is None:
        status = "missing_next_boundary"
    elif _positive_literal(next_literal) is None:
        status = "invalid_next_boundary"
    elif raw_word_count:
        status = "nonempty_zero_span"
    else:
        status = "empty_zero_span"

    greek_next_address: str | None = None
    greek_next_status = "not_checked"
    greek_subverse_count = 0
    next_verse = _positive_literal(next_literal)
    if next_verse is not None:
        greek_next_address = f"Ps {chapter}:{next_verse}"
        if greek_verse is not None:
            node = greek_verse(chapter, next_verse)
            if node is None:
                greek_next_status = "absent"
            else:
                if type(node) is not int or node <= 0:
                    raise ValueError("Greek Psalm verse lookup did not return an original verse node")
                greek_next_status = "present"
                if greek_subverse is not None:
                    child_nodes = tuple(greek_subverse(node))
                    if len(set(child_nodes)) != len(child_nodes):
                        raise ValueError("Greek Psalm subverse children are not unique")
                    greek_subverse_count = len(child_nodes)

    return {
        "source_record_id": document.source_record_id,
        "source_sha256": document.source_sha256,
        "source_chapter": chapter,
        "source_verse_literal": literal,
        "zero_source_tag_offset": start,
        "zero_source_marker_ordinal": 1,
        "source_words_before_zero": prior_words,
        "zero_span_word_count": raw_word_count,
        "next_source_verse_literal": next_literal,
        "greek_next_address": greek_next_address,
        "greek_next_status": greek_next_status,
        "greek_next_subverse_count": greek_subverse_count,
        "status": status,
        "interpretation": "Original source TT zero span topology; no Greek/Coptic text equivalence",
    }


class PsalmZeroAudit:
    """Full immutable-source record census, retaining no Coptic or Greek text."""

    def __init__(self) -> None:
        self._rows: dict[str, dict[str, object]] = {}

    def add(self, document: DocumentModel, observed: dict[str, object] | None) -> None:
        if observed is None:
            raise ValueError("expected a genuine Bohairic Psalm verse-zero observation")
        key = document.source_record_id.casefold()
        if key in self._rows:
            raise ValueError("duplicate Psalm physical source record")
        if (
            observed["source_record_id"] != document.source_record_id
            or observed["source_sha256"] != document.source_sha256
        ):
            raise ValueError("Psalm source record or sha256 does not match evidence")
        self._rows[key] = observed

    def report(self) -> dict[str, object]:
        rows = sorted(self._rows.values(), key=lambda x: int(x["source_chapter"]))
        chapters = [row["source_chapter"] for row in rows]
        if len(chapters) != len(set(chapters)):
            raise ValueError("two distinct physical documents claim the same Psalm chapter")
        counts = Counter(str(row["status"]) for row in rows)
        greek = Counter(str(row["greek_next_status"]) for row in rows)
        return {
            "schema": SCHEMA,
            "source_commit": SOURCE_PIN,
            "lxx_parent_commit": "f32a98eddf7eb239aa73ab863d70381e416d5076",
            "source_records": len(rows),
            "source_zero_markers": len(rows),
            "source_zero_word_slots": sum(int(row["zero_span_word_count"]) for row in rows),
            "counts": dict(sorted(counts.items())),
            "greek_next_status": dict(sorted(greek.items())),
            "examples": sorted(str(row["source_record_id"]) for row in rows)[:3],
            "records": rows,
            "interpretation": "Original Coptic Psalm zero source spans; not Greek verse-zero or certified translations",
        }
