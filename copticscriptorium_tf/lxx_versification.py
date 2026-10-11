"""Byte-qualified Bohairic Zechariah→Rahlfs LXX numbering *candidates*.

Edition/reference crosswalk only. The source translations are attributed to
Brenton (1851) and the pinned source audit supports numerical displacement,
but neither this code nor shared IDs certify Coptic↔Greek textual equivalence.
Source and Greek source references remain distinct and available.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import DocumentModel

BOHAIRIC_ZECH_CROSSWALK_VERSION = "bohairic-zach-lxx1935-v1"
COPTIC_SOURCE_GIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
BOHAIRIC_ZECH_CHAPTER_SHA: dict[int, str] = {
    1: "c52322c9e69a68cefe39827c18417a37d291ecbd919f8440adc0c340cf7867bd",
    2: "6521b293392498f22cddd432bfe2bc0a89ef4a244010040a5b8c3d45a5382028",
}
# An explicit *batch* of scoped, source-edition-specific verse-number rules.
# Source Zech 1:18–21 → pinned Greek Zech 2:1–4.
# Source Zech 2:1–6 → pinned Greek Zech 2:5–10.
_RULES: tuple[tuple[int, range, int], ...] = (
    (1, range(18, 22), -17),
    (2, range(1, 7), 4),
)


@dataclass(frozen=True, slots=True)
class VersificationCandidate:
    lxx_book: str
    lxx_chapter: int
    lxx_verse: int
    rule_id: str
    blocked_reason: str | None = None


def propose_bohairic_zechariah(
    document: DocumentModel,
    *,
    lxx_book: str,
    source_chapter: int,
    source_verse: int,
) -> VersificationCandidate | None:
    """Return an opt-in *candidate* for this exact source edition/bytes.

    A targeted record whose bytes/provenance are wrong blocks same-number
    fallback. Other works/witnesses/verses return None (unchanged).
    """
    if lxx_book != "Zech" or document.corpus != "bohairic.ot":
        return None
    cts = (document.metadata.get("document_cts_urn") or "").strip()
    expected_cts = f"urn:cts:copticLit:ot.zach.bohairic_ed:{source_chapter:02d}"
    if cts != expected_cts:
        # This corpus family is known to contain an edition whose chapter-2
        # numbering differs from Rahlfs. An unreviewed edition of the *same
        # work* must not be given Greek same-number candidate IDs in the
        # implicated chapter boundary (even if numbers happen to exist).
        if (
            (source_chapter == 1 and source_verse >= 18)
            or (source_chapter == 2 and source_verse >= 1)
        ):
            return VersificationCandidate(
                lxx_book="Zech", lxx_chapter=source_chapter,
                lxx_verse=source_verse,
                rule_id=BOHAIRIC_ZECH_CROSSWALK_VERSION,
                blocked_reason="Bohairic Zechariah exact CTS edition not reviewed "
                               "against pinned LXX numbering",
            )
        return None

    offset = next(
        (rule_offset for chapter, verses, rule_offset in _RULES
         if chapter == source_chapter and source_verse in verses),
        None,
    )
    if offset is None:
        if source_chapter == 2 and source_verse >= 7:
            # The same numbered Greek verse *exists* here, but this Bohairic
            # source demonstrably uses a displaced chapter-2 reference
            # system. Downstream unreviewed verses must never silently fall
            # back to potentially false Greek same-number matches.
            return VersificationCandidate(
                lxx_book="Zech", lxx_chapter=2, lxx_verse=source_verse,
                rule_id=BOHAIRIC_ZECH_CROSSWALK_VERSION,
                blocked_reason=(
                    "Bohairic Zechariah chapter 2 numbering differs from "
                    "Rahlfs LXX; verse beyond reviewed 1–6 crosswalk "
                    "requires further source-text adjudication"
                ),
            )
        return None
    candidate = VersificationCandidate(
        lxx_book="Zech",
        lxx_chapter=2,
        lxx_verse=source_verse + offset,
        rule_id=BOHAIRIC_ZECH_CROSSWALK_VERSION,
    )
    expected_record = f"bohairic.ot/bohairic.ot:38_Zacharias_{source_chapter:02d}"
    expected_digest = BOHAIRIC_ZECH_CHAPTER_SHA[source_chapter]
    wrong = (
        document.source_record_id != expected_record
        or document.dataset != "bohairic.ot"
        or document.upstream_repository != "CopticScriptorium/corpora"
        or document.upstream_commit != COPTIC_SOURCE_GIT
        or document.source_sha256 != expected_digest
        or document.metadata.get("chapter", "").lstrip("0") != str(source_chapter)
    )
    if wrong:
        return VersificationCandidate(
            candidate.lxx_book, candidate.lxx_chapter, candidate.lxx_verse,
            candidate.rule_id,
            "edition-specific Zechariah crosswalk requires exact pinned source "
            "record, SHA-256, corpus chapter, and upstream revision",
        )
    return candidate
