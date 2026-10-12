"""Coptic-owned source SBL wrappers to edition-qualified Greek NT verse candidates.

The independently maintained Greek NT TF repository contains no Coptic
alignment work. A matching book/chapter/verse is only a source-backed
reference candidate, NOT certified Greek textual or word correspondence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import re
from typing import Callable, Literal

from .model import DocumentModel
from .nt_paired_verse import paired_word_verses, source_pair_for_sbl

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
MORPHGNT_ABSENT = frozenset({("Mark", 15, 28), ("John", 7, 53)} | {("John", 8, n) for n in range(1, 12)})
# Only these two source identities have the independently checked original
# Mark 1 verse_n + CTS vid_n tags with no verse_vid layer.
PINNED_1COR1_SHORT_VID_BLOB = "87b0c52de46be063c34aa343160103fa9603758a"
PINNED_1COR1_SHORT_VID_RECORDS = frozenset({
    "sahidica.1corinthians/sahidica.1corinthians:1Cor_01",
    "coptic-treebank/coptic.treebank:1Cor_01",
})
MARK1_DUAL_CTS_RECORDS = frozenset({
    "sahidica.mark/sahidica.mark:Mark_01",
    "coptic-treebank/coptic.treebank:Mark_01",
})

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
    """Only documented absent verse addresses in the exact pinned MorphGNT parent."""
    return (book, chapter, verse) in MORPHGNT_ABSENT


def _positive(text: str | None) -> int | None:
    if text is None or not text.isascii() or not text.isdecimal():
        return None
    value = int(text)
    return value if value > 0 else None

_HUMAN_VERSE = re.compile(r"^(Mark|1 Corinthians) ([1-9][0-9]*):([1-9][0-9]*)$")


def _source_verse_number(value: str | None, *, book: str | None, chapter: int | None) -> int | None:
    """Accept only real attested bare or book-qualified source verse styles.

    A full label must agree with BOTH the parent work and its chapter; it
    cannot silently supply a different book, chapter or a forged reference.
    """
    number = _positive(value)
    if number is not None:
        return number
    match = _HUMAN_VERSE.fullmatch(value or "")
    if not match or chapter is None:
        return None
    expected_label = {"Mark": "Mark", "1_Corinthians": "1 Corinthians"}.get(book)
    if match.group(1) != expected_label or int(match.group(2)) != chapter:
        return None
    return int(match.group(3))



def _git_blob_for_document(document: DocumentModel) -> str:
    """Verify the original TT content, not an untrusted Git commit label."""
    raw = document.source_text.encode("utf-8")
    if sha256(raw).hexdigest() != document.source_sha256:
        raise ValueError("Coptic source bytes differ from document SHA256")
    return sha1(f"blob {len(raw)}\\0".encode("ascii") + raw).hexdigest()


def _pinned_1cor1_short_vid(
    *, record: str, source_git_blob: str, ordinal: int, kind: str,
    chapter: int | None, verse: int | None,
    vid: str | None, label: str | None,
) -> bool:
    """Only the TWO exact pinned physical 1Cor1:9 SBL witnesses may use '.9'.

    The suffix is a defective original CTS field, NOT a general CTS syntax.
    Require independent agreeing original verse_n and editor verse_vid,
    original SBL ordinal/kind, and exact Git blob of the source document.
    """
    return (
        record in PINNED_1COR1_SHORT_VID_RECORDS
        and source_git_blob == PINNED_1COR1_SHORT_VID_BLOB
        and type(ordinal) is int and ordinal == 12
        and kind == "sbl_greek" and chapter == 1 and verse == 9
        and vid == ".9" and label == "46N 1:9"
    )


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
    physical_dataset_matches = (
        document.dataset == "coptic.treebank"
        if family == "coptic-treebank"
        else document.dataset == family
    )
    attested = (
        source_info is not None
        and physical_family in REVIEWED_PACKAGES
        and physical_family == family
        and physical_dataset_matches
        and (family == "coptic-treebank"
             or (meta.get("corpus") or "").strip() == family)
        and (meta.get("book") or "").strip() == documented_book_name
        and SOURCE_PROVENANCE_MARKER in (meta.get("Greek_source") or "")
    )
    duplicated_identity = frozenset(document.metadata_duplicates) & frozenset(
        ("book", "chapter", "corpus", "document_cts_urn", "Greek_source")
    )
    doc_cts = CTS_DOCUMENT.fullmatch((meta.get("document_cts_urn") or "").strip())
    paired_words = (
        paired_word_verses(document)
        if (attested and not duplicated_identity and source_info is not None
            and book == "1_Corinthians" and chapter == 14)
        else ()
    )

    for annotation in document.sbl_annotations:
        status: Status = "unresolved"
        reason = ""
        target_node = None
        shared_id = None
        verse = _source_verse_number(annotation.source_verse_n, book=book, chapter=chapter)
        indices = annotation.word_ordinals
        words = tuple(document.words[i - 1] for i in indices
                      if isinstance(i, int) and 1 <= i <= len(document.words))
        raw_verse = {w.verse_n for w in words}
        raw_vid = {w.vid_n for w in words}
        raw_label = {w.verse_vid for w in words}
        vid = next(iter(raw_vid)) if len(raw_vid) == 1 else None
        label = next(iter(raw_label)) if len(raw_label) == 1 else None
        source_pair = (
            source_pair_for_sbl(document, paired_words, indices)
            if (paired_words and annotation.source_verse_n is None
                and raw_verse == {None} and raw_vid == {None})
            else None
        )
        if source_pair is not None and label == source_pair.editor:
            verse = source_pair.number
        else:
            source_pair = None
        evidence = (
            "book+chapter+document_cts_urn+verse_n+"
            + ("vid_n+" if vid is not None else "")
            + "verse_vid+" + annotation.kind
        )

        if source_pair is not None:
            evidence = "book+chapter+document_cts_urn+verse+verse_vid+" + annotation.kind

        if duplicated_identity:
            status, reason = "ambiguous", "duplicate source identity or provenance metadata"
        elif not attested:
            status, reason = "unclassified_source", "unreviewed NT source or missing Greek provenance"
        elif not indices or len(words) != len(indices):
            status, reason = "unresolved", "SBL occurrence has no fully enclosed Coptic word span"
        elif (len(raw_verse) != 1 or len(raw_vid) != 1 or len(raw_label) != 1
              or annotation.source_verse_n not in raw_verse):
            status, reason = "ambiguous", "contradictory source references in Coptic word span"
        else:
            verse_cts = CTS_VERSE.fullmatch(vid) if vid is not None else None
            verse_label = VERSE_LABEL.fullmatch(label or "")
            # Pinned Mark_01 source witnesses retain TWO agreeing original
            # word-scope markers (verse_n and CTS vid_n), but omit the editor
            # verse_vid layer. Unlike one-marker Mark10/11, these can support
            # a verse-address candidate. Fail closed for crossed/shifted
            # sbl_greek values that actually contain an editor ref.
            dual_mark1_cts = (
                document.source_record_id in MARK1_DUAL_CTS_RECORDS
                and book == "Mark" and chapter == 1
                and label is None
                and verse_cts is not None
                and not (annotation.kind == "sbl_greek" and (
                    not (annotation.value or "").strip()
                    or VERSE_LABEL.fullmatch((annotation.value or "").strip())
                    or CTS_VERSE.fullmatch((annotation.value or "").strip())
                ))
            )
            if dual_mark1_cts:
                evidence = "book+chapter+document_cts_urn+verse_n+vid_n+" + annotation.kind
            short_1cor1 = False
            if (
                document.source_record_id in PINNED_1COR1_SHORT_VID_RECORDS
                and annotation.kind == "sbl_greek"
                and annotation.ordinal == 12
                and book == "1_Corinthians" and chapter == 1 and verse == 9
                and vid == ".9" and label == "46N 1:9"
            ):
                short_1cor1 = _pinned_1cor1_short_vid(
                    record=document.source_record_id,
                    source_git_blob=_git_blob_for_document(document),
                    ordinal=annotation.ordinal, kind=annotation.kind,
                    chapter=chapter, verse=verse, vid=vid, label=label,
                )
            if short_1cor1:
                evidence = "book+chapter+document_cts_urn+verse_n+verse_vid+gitblob-verified-short-vid_n+" + annotation.kind
            # Actual Mark TT chapters may omit vid_n entirely. Accept that
            # absence only when the Coptic verse_n, document CTS and explicit
            # verse_vid editor reference corroborate each other.
            if not doc_cts or (not verse_label and not dual_mark1_cts) or (vid is not None and not verse_cts and not short_1cor1):
                status, reason = "ambiguous", "missing or malformed source NT reference evidence"
            elif (doc_cts.group(1) != documented_work
                  or (verse_label is not None
                      and verse_label.group(1) != documented_label)
                  or chapter is None or verse is None
                  or _positive(doc_cts.group(2)) != chapter
                  or (verse_cts is not None and (
                      verse_cts.group(1) != documented_work
                      or _positive(verse_cts.group(2)) != chapter
                      or _positive(verse_cts.group(3)) != verse
                  ))
                  or (verse_label is not None and (
                      _positive(verse_label.group(2)) != chapter
                      or _positive(verse_label.group(3)) != verse
                  ))):
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
