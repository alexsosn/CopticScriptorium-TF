"""Coptic-owned source SBL wrappers to edition-qualified Greek NT verse candidates.

The independently maintained Greek NT TF repository contains no Coptic
alignment work. A matching book/chapter/verse is only a source-backed
reference candidate, NOT certified Greek textual or word correspondence.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Literal

from .model import DocumentModel

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
GREEK_NT_EDITION = "morphgnt/sblgnt:6.12:aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d"
SOURCE_PROVENANCE_MARKER = "SBL Greek New Testament"

# The two reviewed, actually annotated Greek-NT book families in pinned TT.
# coptic-treebank is an independent physical source packaging for these works.
REVIEWED_SOURCES = {
    "sahidica.mark": ("Mark", "mark", "41N", "Mark"),
    "sahidica.1corinthians": ("1_Corinthians", "1cor", "46N", "1Cor"),
}
REVIEWED_PACKAGES = frozenset((*REVIEWED_SOURCES, "coptic-treebank"))
CTS_DOCUMENT = re.compile(r"^urn:cts:copticLit:nt\.([a-z0-9]+)\.sahidica_ed:([1-9][0-9]*)$")
CTS_VERSE = re.compile(r"^urn:cts:copticLit:nt\.([a-z0-9]+)\.sahidica_ed:([1-9][0-9]*)\.([1-9][0-9]*)$")
VERSE_LABEL = re.compile(r"^(41N|46N) ([1-9][0-9]*):([1-9][0-9]*)$")
MORPHGNT_ABSENT = frozenset({("John", 7, 53)} | {("John", 8, n) for n in range(1, 12)})

Status = Literal["reference_candidate", "unresolved", "ambiguous",
                 "edition_unavailable", "unclassified_source"]
VerseLookup = Callable[[str, int, int], int | None]


@dataclass(frozen=True, slots=True)
class CopticSblReference:
    source_record_id: str
    source_ordinal: int
    source_kind: str
    source_word_ordinals: tuple[int, ...]
    source_verse_n: str | None
    source_vid_n: str | None
    source_verse_vid: str | None
    target_book: str | None
    target_chapter: int | None
    target_verse: int | None
    target_node: int | None
    shared_id: str | None
    status: Status
    evidence: str
    reason: str


def morphgnt_verse_is_absent(book: str, chapter: int, verse: int) -> bool:
    """Explicitly reviewed Faithlife-v1.2 additions missing from MorphGNT."""
    return (book, chapter, verse) in MORPHGNT_ABSENT


def _positive(text: str | None) -> int | None:
    if text is None or not text.isascii() or not text.isdecimal():
        return None
    value = int(text)
    return value if value > 0 else None


def resolve_coptic_sbl_references(
    document: DocumentModel, *, lookup: VerseLookup,
) -> tuple[CopticSblReference, ...]:
    """Return one source-qualified result per physical SBL annotation.

    Parent TF node IDs are only used in this in-process diagnostic result.
    Output TF modules must write stable shared strings, never foreign IDs.
    """
    if (document.upstream_repository != "CopticScriptorium/corpora"
            or document.upstream_commit != COPTIC_PIN):
        raise ValueError("unverified Coptic source revision")
    results: list[CopticSblReference] = []
    meta = document.metadata
    family = document.corpus
    physical_family = document.source_record_id.partition("/")[0]
    # coptic-treebank is physical derivative packaging. The upstream meta
    # corpus is the attested original family; both identities are preserved,
    # never collapsed into one source record.
    source_info = REVIEWED_SOURCES.get(family)
    if (family == "coptic-treebank" and document.dataset == "coptic.treebank"
            and physical_family == "coptic-treebank"):
        source_info = REVIEWED_SOURCES.get((meta.get("corpus") or "").strip())
    chapter = _positive(meta.get("chapter"))
    book = source_info[0] if source_info else None
    documented_work = source_info[1] if source_info else None
    documented_label = source_info[2] if source_info else None
    documented_book_name = source_info[3] if source_info else None
    attested = (
        source_info is not None
        and physical_family in REVIEWED_PACKAGES
        and (physical_family == family)
        and (family == "coptic-treebank"
             or (meta.get("corpus") or "").strip() == family)
        and (meta.get("book") or "").strip() == documented_book_name
        and SOURCE_PROVENANCE_MARKER in (meta.get("Greek_source") or "")
    )
    doc_cts = CTS_DOCUMENT.fullmatch((meta.get("document_cts_urn") or "").strip())

    for annotation in document.sbl_annotations:
        status: Status = "unresolved"
        reason = ""
        target_node = None
        shared_id = None
        verse = _positive(annotation.source_verse_n)
        indices = annotation.word_ordinals
        words = tuple(document.words[i - 1] for i in indices
                      if isinstance(i, int) and 1 <= i <= len(document.words))
        raw_verse = {w.verse_n for w in words}
        raw_vid = {w.vid_n for w in words}
        raw_label = {w.verse_vid for w in words}
        vid = next(iter(raw_vid)) if len(raw_vid) == 1 else None
        label = next(iter(raw_label)) if len(raw_label) == 1 else None
        evidence = "book+chapter+document_cts_urn+verse_n+vid_n+verse_vid+" + annotation.kind

        if not attested:
            status, reason = "unclassified_source", "unreviewed NT source or missing Greek provenance"
        elif not indices or len(words) != len(indices):
            status, reason = "unresolved", "SBL occurrence has no fully enclosed Coptic word span"
        elif (len(raw_verse) != 1 or len(raw_vid) != 1 or len(raw_label) != 1
              or annotation.source_verse_n not in raw_verse):
            status, reason = "ambiguous", "contradictory source references in Coptic word span"
        else:
            verse_cts = CTS_VERSE.fullmatch(vid or "")
            verse_label = VERSE_LABEL.fullmatch(label or "")
            if not doc_cts or not verse_cts or not verse_label:
                status, reason = "ambiguous", "missing or malformed source NT reference evidence"
            elif (doc_cts.group(1) != documented_work
                  or verse_cts.group(1) != documented_work
                  or verse_label.group(1) != documented_label
                  or chapter is None or verse is None
                  or _positive(doc_cts.group(2)) != chapter
                  or _positive(verse_cts.group(2)) != chapter
                  or _positive(verse_cts.group(3)) != verse
                  or _positive(verse_label.group(2)) != chapter
                  or _positive(verse_label.group(3)) != verse):
                status, reason = "ambiguous", "contradictory NT book/chapter/verse evidence"
            elif morphgnt_verse_is_absent(book, chapter, verse):
                status, reason = "edition_unavailable", "verse absent from pinned MorphGNT edition"
            else:
                target_node = lookup(book, chapter, verse)
                if target_node is None:
                    status, reason = "unresolved", "address unavailable in pinned Greek NT TF"
                elif (not isinstance(target_node, int)
                      or isinstance(target_node, bool) or target_node <= 0):
                    raise ValueError("Greek NT lookup must return positive parent node or None")
                else:
                    status = "reference_candidate"
                    reason = "matching edition-qualified verse address; textual equivalence unverified"
                    shared_id = f"{GREEK_NT_EDITION}:{book}:{chapter}:{verse}"
        results.append(CopticSblReference(
            source_record_id=document.source_record_id,
            source_ordinal=annotation.ordinal,
            source_kind=annotation.kind,
            source_word_ordinals=annotation.word_ordinals,
            source_verse_n=annotation.source_verse_n,
            source_vid_n=vid,
            source_verse_vid=label,
            target_book=book,
            target_chapter=chapter,
            target_verse=verse,
            target_node=target_node,
            shared_id=shared_id,
            status=status,
            evidence=evidence,
            reason=reason,
        ))
    return tuple(results)
