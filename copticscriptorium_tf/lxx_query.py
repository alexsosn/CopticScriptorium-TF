"""Researcher-facing inverse lookup of Coptic OT *reference candidates* from LXX.

The Coptic and CenterBLC/LXX native TF APIs are separate warps. Join ONLY by
the stable edition-qualified shared reference feature, never by integer nodes.
Both parent corpora and their respective additive modules must be loaded and
their immutable parent identities verified separately before scholarly use.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CANDIDATE_STATUSES = frozenset({"reference_candidate", "versification_candidate"})
LXX_EDITION = "CenterBLC/LXX:1935"
INTERPRETATION = (
    "Matching edition-qualified *reference-address candidates*, not "
    "verified Coptic/Greek passage equivalence or word alignment"
)


class LxxWitnessQueryError(ValueError):
    """Missing, corrupt or inconsistent native Coptic↔LXX module evidence."""


@dataclass(frozen=True, slots=True)
class CopticWitnessSpan:
    source_record_id: str
    source_word_ordinals: tuple[int, ...]
    word_nodes: tuple[int, ...]  # Only within the Coptic TF warp
    status: str


@dataclass(frozen=True, slots=True)
class LxxCopticWitnessResult:
    book: str
    chapter: int
    verse: int
    lxx_node: int  # Only within the LXX TF warp
    shared_id: str
    declared_coptic_source_span_count: int
    spans: tuple[CopticWitnessSpan, ...]
    interpretation: str = INTERPRETATION


def _feature(api: Any, name: str, *, corpus: str) -> Any:
    try:
        value = getattr(api.F, name)
    except (AttributeError, LookupError) as exc:
        raise LxxWitnessQueryError(
            f"missing {corpus} native TF module feature {name}"
        ) from exc
    if not callable(getattr(value, "v", None)):
        raise LxxWitnessQueryError(
            f"missing {corpus} native TF module feature {name}"
        )
    return value


def _positive_node(node: object) -> bool:
    return type(node) is int and node > 0


def find_coptic_witnesses(
    coptic_api: Any, lxx_api: Any, book: str, chapter: int, verse: int,
) -> LxxCopticWitnessResult:
    """Find *all* locally loaded Coptic witness word runs for one Greek verse.

    Requires two separately loaded TF APIs with their appropriate `coptic_lxx_*`
    native weft features. The caller should independently verify pinned parent
    corpora with `verify_coptic_module_parent` / `validate_lxx_release`.

    Uses the TF feature's inverted `.s(shared_id)` index; does not enumerate
    2.4 million Coptic word slots. Original physical document and source word
    ordinals are preserved; adjacent candidate runs are grouped only within
    the same physical source record **and same mapping status**.
    """
    if (
        not isinstance(book, str) or not book or any(c in book for c in " \t\n:")
        or type(chapter) is not int or chapter <= 0
        or type(verse) is not int or verse <= 0
    ):
        raise LxxWitnessQueryError("invalid exact LXX book/chapter/verse address")
    shared = f"{LXX_EDITION}:{book}:{chapter}:{verse}"
    node = lxx_api.T.nodeFromSection((book, chapter, verse))
    if not _positive_node(node):
        raise LxxWitnessQueryError(f"no LXX verse at {book} {chapter}:{verse}")
    if _feature(lxx_api, "otype", corpus="LXX").v(node) != "verse":
        raise LxxWitnessQueryError("LXX section is not a verse node")
    greek_id = _feature(lxx_api, "coptic_lxx_ref_id", corpus="LXX").v(node)
    if greek_id != shared:
        raise LxxWitnessQueryError(
            "LXX native module has missing or wrong edition-qualified shared reference"
        )
    count = _feature(
        lxx_api, "coptic_lxx_source_span_count", corpus="LXX"
    ).v(node)
    if not _positive_node(count):
        raise LxxWitnessQueryError("invalid LXX declared Coptic source span count")

    ids = _feature(coptic_api, "coptic_lxx_ref_id", corpus="Coptic")
    if not callable(getattr(ids, "s", None)):
        raise LxxWitnessQueryError(
            "missing Coptic inverse native TF module feature index"
        )
    candidates = tuple(ids.s(shared))
    if not candidates:
        raise LxxWitnessQueryError(
            "LXX weft declares candidate spans but no Coptic native word references exist"
        )
    statuses = _feature(coptic_api, "coptic_lxx_ref_status", corpus="Coptic")
    record_id = _feature(coptic_api, "source_record_id", corpus="Coptic")
    ordinals = _feature(coptic_api, "source_word_ordinal", corpus="Coptic")
    types = _feature(coptic_api, "otype", corpus="Coptic")
    seen_source_words: set[tuple[str, int]] = set()
    entries: list[tuple[str, int, int, str]] = []

    for word in candidates:
        if not _positive_node(word) or types.v(word) != "word":
            raise LxxWitnessQueryError(f"non-word Coptic candidate node {word!r}")
        if ids.v(word) != shared:
            raise LxxWitnessQueryError("inverted Coptic reference index is inconsistent")
        source = record_id.v(word)
        source_ordinal = ordinals.v(word)
        status = statuses.v(word)
        if not isinstance(source, str) or not source:
            raise LxxWitnessQueryError("Coptic candidate lacks physical source_record_id")
        if not _positive_node(source_ordinal):
            raise LxxWitnessQueryError("Coptic candidate has invalid source word ordinal")
        if status not in CANDIDATE_STATUSES:
            raise LxxWitnessQueryError(f"invalid Coptic reference candidate status {status!r}")
        identity = (source, source_ordinal)
        if identity in seen_source_words:
            raise LxxWitnessQueryError(
                f"duplicate physical Coptic source word reference {identity}"
            )
        seen_source_words.add(identity)
        entries.append((source, source_ordinal, word, status))

    entries.sort(key=lambda item: (item[0], item[1], item[2]))
    if count < len({item[0] for item in entries}):
        raise LxxWitnessQueryError(
            "LXX declared source span count smaller than distinct Coptic witnesses"
        )

    spans: list[CopticWitnessSpan] = []
    active_source = ""
    active_status = ""
    active_ordinals: list[int] = []
    active_words: list[int] = []

    def flush() -> None:
        if active_ordinals:
            spans.append(CopticWitnessSpan(
                source_record_id=active_source,
                source_word_ordinals=tuple(active_ordinals),
                word_nodes=tuple(active_words),
                status=active_status,
            ))

    for source, source_ordinal, word, status in entries:
        if (
            active_ordinals
            and source == active_source
            and status == active_status
            and source_ordinal == active_ordinals[-1] + 1
        ):
            active_ordinals.append(source_ordinal)
            active_words.append(word)
        else:
            flush()
            active_source, active_status = source, status
            active_ordinals = [source_ordinal]
            active_words = [word]
    flush()

    return LxxCopticWitnessResult(
        book=book, chapter=chapter, verse=verse, lxx_node=node,
        shared_id=shared, declared_coptic_source_span_count=count,
        spans=tuple(spans),
    )
