"""Source-byte-locked, read-only Psalm0 vs Greek Psalm1–2 boundary evidence.

This is a *diagnostic*. It cannot assert word translation, same passage or
whole-verse agreement; existing parent-specific TF wefts stay unchanged.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence
import unicodedata

from .model import DocumentModel
from .psalm_zero_boundary import SOURCE_PIN, inspect_psalm_zero

LXX_PIN = "f32a98eddf7eb239aa73ab863d70381e416d5076"
SCHEMA = "bohairic_psalm_zero_lxx_first_two_verse_anchors_v1"
SELECTED_SOURCE_SHA: dict[int, str] = {
    1: "d29334067d8fa375a222cc2025ea0bfdaf5e01edc441c5813593f233ec3c1dbe",
    3: "cbeb4996b0cd142e888bcd630eaac6123af05d7084d49b614066fa9799b5b9d6",
    17: "0fc5384f9baa44f0d4a180539b84b9cf06f5a3be5176360fdf7b27c9451e3af3",
    51: "fd179fe092f1adc0feb4bf4b9c0ae38a001175c18e745db014a8ca6bb7231d64",
    149: "b6e6856db848f193849a8c76cce7dda36170438bf8ee373f3d873b7cb4739c7d",
    151: "4e15361ffa0edcb25b9e782a3961f385cde039000e791840474ee7fc759d4afd",
}
EXPECTED_ZERO_WORDS = {1: 1, 3: 16, 17: 59, 51: 42, 149: 1, 151: 11}
STATUSES = frozenset({
    "source_editorial_placeholder", "cross_greek_verse_boundary_candidate",
    "within_first_greek_verse_candidate", "needs_primary_collation",
})


def _canonical_word(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("source or Greek word is not a Unicode string")
    # Accent/punctuation-insensitive comparison only for the *short* curated
    # anchor motifs, not for broad automated lexical similarity.
    n = unicodedata.normalize("NFD", value.casefold())
    return "".join(
        c for c in n if unicodedata.category(c)[0] == "L"
    )


def classify_psalm_boundary(
    chapter: int,
    source_zero: Sequence[str],
    source_one: Sequence[str],
    greek_one: Sequence[str],
    greek_two: Sequence[str],
) -> dict[str, object]:
    """Classify only three independent, deliberately weak source/Gk anchors.

    All remaining source Psalms stay `needs_primary_collation` even when they
    have nonempty titles. No LXX verse/word ID is manufactured by this function.
    """
    if chapter not in SELECTED_SOURCE_SHA or not source_zero or not source_one:
        raise ValueError("unsupported Psalm or missing original Coptic source words")
    if not greek_one or not greek_two:
        raise ValueError("missing original Greek first or second verse words")
    if any(not isinstance(w, str) or not w for w in (*source_zero, *source_one, *greek_one, *greek_two)):
        raise ValueError("missing source/Greek verse word form")
    z = tuple(_canonical_word(w) for w in source_zero)
    g1 = tuple(_canonical_word(w) for w in greek_one)
    g2 = tuple(_canonical_word(w) for w in greek_two)
    src_placeholder = len(source_zero) == 1 and source_zero[0].strip() == "..."
    src_hallelujah = len(z) == 1 and z[0] == "ⲁⲗⲗⲏⲗⲟⲩⲓⲁ"
    greek_hallelujah = g1[0] in {"αλληλουια", "αλληλουιας"}
    # Coptic Scriptorium may split ⲡⲉϫⲁϥ at a token boundary.
    # Need *both* the conjunction and the saying verb, not "said" alone.
    coptic_and_said = "".join(z[-5:]).endswith("ⲟⲩⲟϩⲡⲉϫⲁϥ")
    greek_and_said = len(g2) >= 2 and g2[:2] == ("και", "ειπεν")
    if chapter == 1 and src_placeholder and g1[0] == "μακαριοσ":
        status = "source_editorial_placeholder"
    elif chapter == 17 and coptic_and_said and greek_and_said:
        status = "cross_greek_verse_boundary_candidate"
    elif chapter == 149 and src_hallelujah and greek_hallelujah:
        status = "within_first_greek_verse_candidate"
    else:
        status = "needs_primary_collation"
    return {
        "status": status,
        "source_ellipsis": src_placeholder,
        "source_hallelujah": src_hallelujah,
        "greek_verse_one_begins_hallelujah": greek_hallelujah,
        "coptic_and_said_at_zero_end": coptic_and_said,
        "greek_and_said_at_verse_two_start": greek_and_said,
        "source0_to_greek_verse_whole": False,
        "greek_reference_verified": False,
    }


def inspect_selected_psalm(
    document: DocumentModel,
    *,
    greek_words: Callable[[int, int], Sequence[str]],
) -> dict[str, object]:
    """Require exactly one of six physical TT SHA-locked source witnesses."""
    if (
        document.upstream_repository != "CopticScriptorium/corpora"
        or document.upstream_commit != SOURCE_PIN
        or not isinstance(document.source_text, str)
        or sha256(document.source_text.encode("utf-8")).hexdigest()
        != document.source_sha256
    ):
        raise ValueError("Psalm source revision or SHA pin mismatch")
    first = inspect_psalm_zero(document)
    if first is None:
        raise ValueError("no exact Bohairic Psalm source witness")
    chapter = first["source_chapter"]
    if (
        chapter not in SELECTED_SOURCE_SHA
        or document.source_sha256 != SELECTED_SOURCE_SHA[chapter]
        or first["zero_span_word_count"] != EXPECTED_ZERO_WORDS[chapter]
        or first["next_source_verse_literal"] != "1"
    ):
        raise ValueError("unsupported exact Psalm source record SHA/word count pin")
    source0 = tuple(w.norm for w in document.words if w.verse_n == "0")
    source1 = tuple(w.norm for w in document.words if w.verse_n == "1")
    g1 = tuple(greek_words(chapter, 1))
    g2 = tuple(greek_words(chapter, 2))
    evidence = classify_psalm_boundary(chapter, source0, source1, g1, g2)
    # Never write content: report only count/status and separately cited source
    # sha. Latinized/normalized lexical anchor checks are a weak hypothesis.
    return {
        "chapter": chapter,
        "source_record_id": document.source_record_id,
        "source_sha256": document.source_sha256,
        "source_zero_word_count": len(source0),
        "source_one_word_count": len(source1),
        "greek_verse_one_word_count": len(g1),
        "greek_verse_two_word_count": len(g2),
        "status": evidence["status"],
        "evidence": {
            k: v for k, v in evidence.items() if k not in {
                "status", "source0_to_greek_verse_whole", "greek_reference_verified"
            }
        },
        "greek_reference_verified": False,
        "interpretation": (
            "Pinned original word-order anchor diagnostic only; no Coptic↔Greek "
            "whole-verse or word alignment"
        ),
    }


class PsalmBoundaryReview:
    """Aggregate immutable metadata for the six selected Psalm witnesses."""

    def __init__(self) -> None:
        self._rows: dict[int, dict[str, object]] = {}

    def add(self, record: Mapping[str, object]) -> None:
        chapter = record["chapter"]
        if type(chapter) is not int or chapter not in SELECTED_SOURCE_SHA:
            raise ValueError("unsupported source Psalm chapter")
        if chapter in self._rows:
            raise ValueError("duplicate source Psalm boundary record")
        if (
            record["source_sha256"] != SELECTED_SOURCE_SHA[chapter]
            or record["source_record_id"] != (
                f"bohairic.ot/bohairic.ot:19_Psalmi_{chapter:03d}"
            )
            or record["status"] not in STATUSES
            or record["greek_reference_verified"] is not False
            or record["source_zero_word_count"] != EXPECTED_ZERO_WORDS[chapter]
        ):
            raise ValueError("Psalm boundary source provenance or status mismatch")
        self._rows[chapter] = dict(record)

    def report(self) -> dict[str, object]:
        rows = [self._rows[k] for k in sorted(self._rows)]
        return {
            "schema": SCHEMA,
            "source_commit": SOURCE_PIN,
            "lxx_parent_commit": LXX_PIN,
            "cases": len(rows),
            "total_coptic_zero_words": sum(int(row["source_zero_word_count"]) for row in rows),
            "statuses": dict(sorted(Counter(str(row["status"]) for row in rows).items())),
            "records": rows,
            "interpretation": (
                "Exact pinned source and Greek word-order anchors only; "
                "NO certified Greek/Coptic translation or whole-verse map"
            ),
        }
