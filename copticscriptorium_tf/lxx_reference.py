"""Strict, source-evidence-based Coptic OT → LXX *reference candidates*.

This is not a Coptic↔Greek word alignment, nor a presumption that identical
verse numbers prove that passages follow the same versification. See issue #70.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Literal

from .model import DocumentModel, Word

# Deliberately limited to source families actually inspected in pinned TT.
# Do not guess every Bible-book/dataset name from substrings.
CORPUS_LXX_BOOK: dict[str, str] = {
    "sahidic.ruth": "Ruth",
    "sahidic.jonah": "Jonah",
    "bohairic-habakkuk": "Hab",
    "bohairic.habakkuk": "Hab",
}
BOOK_ALIASES = {
    "ruth": "Ruth",
    "jonah": "Jonah",
    "habakkuk": "Hab",
    "hab": "Hab",
}
# Compare the *work* identity too, not only matching numeric CTS suffixes.
# Edition spelling can vary (e.g. copto_edt vs coptot_ed in real Ruth).
CTS_WORK_BY_BOOK = {
    "Ruth": re.compile(r"^urn:cts:copticLit:ot\.ruth\.[^:]+:(\d+)\.(\d+)$"),
    "Jonah": re.compile(r"^urn:cts:copticLit:ot\.jonah\.[^:]+:(\d+)\.(\d+)$"),
    "Hab": re.compile(r"^urn:cts:copticLit:ot\.hab\.[^:]+:(\d+)\.(\d+)$"),
}
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
    book = CORPUS_LXX_BOOK.get(document.corpus)
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
                "source family not yet covered by reviewed Coptic OT book mapping; "
                "biblical or nonbiblical status must not be guessed"
            )
        elif not chapter or not verse:
            status, reason = "unresolved", "no valid positive chapter/verse source reference"
        elif len(cts_set) > 1 or len(label_set) > 1:
            status, reason = "ambiguous", "contradictory source reference literals in one word span"
        else:
            meta_book = document.metadata.get("book")
            if meta_book is not None and BOOK_ALIASES.get(meta_book.strip().casefold()) != book:
                status, reason = "ambiguous", "book metadata contradicts reviewed corpus identity"
            elif cts_set and (
                not (match := CTS_WORK_BY_BOOK[book].fullmatch(cts or ""))
                or (int(match[1]), int(match[2])) != (chapter, verse)
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
