"""Strict, source-evidence-based Coptic OT → LXX *reference candidates*.

This is not a Coptic↔Greek word alignment, nor a presumption that identical
verse numbers prove that passages follow the same versification. See issue #70.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Literal

from .model import DocumentModel, Word

# All families below occur in the immutable full-source OT profile; this is
# a reviewed evidence gate, not a guess from a filename or an NT verse marker.
CORPUS_LXX_BOOK: dict[str, str] = {
    "sahidic.ruth": "Ruth",
    "sahidic.jonah": "Jonah",
    "bohairic-jonah": "Jonah",
    "bohairic-habakkuk": "Hab",
    "bohairic.habakkuk": "Hab",  # source dataset spelling
}
MULTIWORK_FAMILIES = frozenset({
    "sahidic.ot", "bohairic.ot", "coptic-treebank", "bohairic-treebank",
})

# Manual alias review of 49 distinct real pinned CTS work strings, checked
# against the book-code inventory of CenterBLC/LXX v1.0.1 (CATSS-TF profile).
# These identify candidate *addresses* only, not Greek textual equivalence.
CTS_WORK_TO_LXX: dict[str, str] = {
    "gen": "Gen", "exod": "Exod", "lev": "Lev", "num": "Num",
    "deut": "Deut", "josh": "Josh", "judg": "Judg", "ruth": "Ruth",
    "1sam": "1Sam", "2sam": "2Sam", "1kgs": "1Kgs", "2kgs": "2Kgs",
    "1chr": "1Chr", "2chr": "2Chr", "2macc": "2Mac",
    "esth": "Esth", "jdt": "Jdt", "pss": "Ps",
    "prov": "Prov", "eccl": "Qoh", "song": "Cant",
    "job": "Job", "wis": "Wis", "sir": "Sir",
    "hos": "Hos", "mic": "Mic", "amos": "Amos", "joel": "Joel",
    "jonah": "Jonah", "obad": "Obad", "nah": "Nah",
    "hab": "Hab", "zeph": "Zeph", "hag": "Hag",
    "zach": "Zech", "zech": "Zech", "mal": "Mal",
    "isa": "Isa", "jer": "Jer", "bar": "Bar", "epjer": "EpJer",
    "lam": "Lam", "ezek": "Ezek",
}
# Deliberately no entries for dan/tob/sus/bel/prman:
# Greek edition choice or target book is underdetermined from the CTS work.
AMBIGUOUS_OR_UNSUPPORTED_WORKS = frozenset({"dan", "tob", "sus", "bel", "prman"})

BOOK_ALIASES = {
    "ruth": "Ruth", "jonah": "Jonah", "habakkuk": "Hab", "hab": "Hab",
    "genesis": "Gen", "exodus": "Exod", "leviticus": "Lev",
    "numbers": "Num", "deuteronomy": "Deut",
    "psalms": "Ps", "psalm": "Ps", "ecclesiastes": "Qoh",
    "song of songs": "Cant", "zechariah": "Zech",
}
# Full namespace/work identity required, not a matched trailing substring.
DOC_CTS = re.compile(
    r"^urn:cts:copticLit:ot\.([A-Za-z0-9_-]+)\.[^:]+:(\d+)$"
)
VERSE_CTS = re.compile(
    r"^urn:cts:copticLit:ot\.([A-Za-z0-9_-]+)\.[^:]+:(\d+)\.(\d+)$"
)


LXX_REFERENCE_EDITION = "CenterBLC/LXX:1935"
VERSE_VID = re.compile(r"^([A-Za-z][A-Za-z ]*) (\d+):(\d+)$")

MappingStatus = Literal[
    "reference_candidate", "unresolved", "ambiguous", "unclassified_corpus"
]


@dataclass(frozen=True, slots=True)
class CopticLxxReference:
    source_record_id: str
    source_word_ordinals: tuple[int, ...]
    source_verse_n: str | None
    source_vid_n: str | None
    source_verse_vid: str | None
    lxx_book: str | None
    lxx_chapter: int | None
    lxx_verse: int | None
    lxx_node: int | None
    shared_id: str | None
    status: MappingStatus
    evidence: str
    reason: str


LxxVerseLookup = Callable[[str, int, int], int | None]


def _positive_int(value: str | None) -> int | None:
    if value is None or not value.isascii() or not value.isdecimal():
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _group_words(document: DocumentModel) -> tuple[tuple[Word, ...], ...]:
    groups: list[list[Word]] = []
    for word in document.words:
        if not groups or groups[-1][-1].verse_n != word.verse_n:
            groups.append([word])
        else:
            groups[-1].append(word)
    return tuple(tuple(group) for group in groups)


def _unique_markers(group: tuple[Word, ...], field: str) -> set[str]:
    return {value for word in group if (value := getattr(word, field)) is not None}


def _source_book(document: DocumentModel) -> tuple[str | None, str | None]:
    """Return a curated LXX book code and optional contradictory-source reason.

    A multi-work OT archive or treebank must have an exact document CTS work;
    book-like source paths or bare metadata labels cannot authorize mapping.
    """
    family = document.corpus
    if family not in CORPUS_LXX_BOOK and family not in MULTIWORK_FAMILIES:
        return None, "source family outside reviewed Coptic OT scope"
    family_book = CORPUS_LXX_BOOK.get(family)
    source_cts = (document.metadata.get("document_cts_urn") or "").strip()
    if not source_cts:
        if family in MULTIWORK_FAMILIES:
            return None, "multi-work family lacks exact OT document CTS work"
        return family_book, None

    match = DOC_CTS.fullmatch(source_cts)
    if match is None:
        return family_book, "invalid or non-OT document CTS identity"
    raw_work, chapter_text = match.groups()
    book = CTS_WORK_TO_LXX.get(raw_work.casefold())
    if book is None:
        return None, (
            "ambiguous target LXX edition or unreviewed CTS work: " + raw_work
        )
    if family_book is not None and family_book != book:
        return family_book, "document CTS work contradicts single-book family"
    chapter_literal = document.metadata.get("chapter")
    if (_positive_int(chapter_text) is None or
            _positive_int(chapter_literal) != _positive_int(chapter_text)):
        return book, "document CTS chapter contradicts source metadata chapter"
    return book, None


def resolve_coptic_lxx_references(
    document: DocumentModel,
    *,
    lookup: LxxVerseLookup,
) -> tuple[CopticLxxReference, ...]:
    """Resolve source-local word spans to *candidate* Greek verse addresses.

    `lookup` must query the actual version-pinned CenterBLC/LXX verse section
    when used operationally. Synthetic callbacks alone cannot validate a
    real-parent mapping. Never emit a successful mapping from contradictory
    `verse_n`, `verse_vid`, `vid_n` or book evidence.
    """
    groups = _group_words(document)
    book, document_issue = _source_book(document)
    result: list[CopticLxxReference] = []

    for group in groups:
        raw_verse = group[0].verse_n
        cts_set = _unique_markers(group, "vid_n")
        label_set = _unique_markers(group, "verse_vid")
        cts = next(iter(cts_set)) if len(cts_set) == 1 else None
        label = next(iter(label_set)) if len(label_set) == 1 else None
        chapter = _positive_int(document.metadata.get("chapter"))
        verse = _positive_int(raw_verse)
        reason: str = ""
        status: MappingStatus = "unresolved"
        target: int | None = None
        shared: str | None = None
        evidence = "+".join(
            x for x, found in (
                ("verse_n", raw_verse is not None),
                ("vid_n", bool(cts_set)),
                ("verse_vid", bool(label_set)),
            ) if found
        ) or "none"

        if book is None:
            status, reason = "unclassified_corpus", (
                document_issue or "unreviewed source work or ambiguous Greek edition"
            )
        elif document_issue:
            status, reason = "ambiguous", document_issue
        elif not chapter or not verse:
            status, reason = "unresolved", "no valid positive chapter/verse source reference"
        elif len(cts_set) > 1 or len(label_set) > 1:
            status, reason = "ambiguous", "contradictory source reference literals in one word span"
        else:
            meta_book = document.metadata.get("book")
            if meta_book is not None and BOOK_ALIASES.get(meta_book.strip().casefold()) != book:
                status, reason = "ambiguous", "book metadata contradicts reviewed corpus identity"
            elif cts_set and (
                not (match := VERSE_CTS.fullmatch(cts or ""))
                or CTS_WORK_TO_LXX.get(match[1].casefold()) != book
                or (int(match[2]), int(match[3])) != (chapter, verse)
            ):
                status, reason = "ambiguous", "CTS work/chapter/verse contradicts source corpus reference"
            elif label_set and (
                not (match := VERSE_VID.fullmatch(label or ""))
                or BOOK_ALIASES.get(match[1].strip().casefold()) != book
                or (int(match[2]), int(match[3])) != (chapter, verse)
            ):
                status, reason = "ambiguous", "source verse label contradicts book/chapter/verse"
            else:
                target = lookup(book, chapter, verse)
                if target is None:
                    status, reason = "unresolved", "exact address absent in provided LXX verse index"
                elif not isinstance(target, int) or isinstance(target, bool) or target <= 0:
                    raise ValueError("LXX verse lookup must return a positive parent node or None")
                else:
                    status, reason = "reference_candidate", (
                        "matching LXX reference address exists; textual equivalence not established"
                    )
                    shared = f"{LXX_REFERENCE_EDITION}:{book}:{chapter}:{verse}"

        result.append(CopticLxxReference(
            source_record_id=document.source_record_id,
            source_word_ordinals=tuple(word.ordinal for word in group),
            source_verse_n=raw_verse,
            source_vid_n=cts,
            source_verse_vid=label,
            lxx_book=book,
            lxx_chapter=chapter,
            lxx_verse=verse,
            lxx_node=target,
            shared_id=shared,
            status=status,
            evidence=evidence,
            reason=reason,
        ))
    return tuple(result)
