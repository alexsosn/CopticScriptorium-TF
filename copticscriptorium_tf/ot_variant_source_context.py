"""Exact-source-context diagnostics for undecided Coptic OT edition gaps.

This intentionally reads original TT *markup*, not translations, and emits
only structural counts and editorial-name mention indicators. A numerical
gap or an editorial mention does NOT identify the Coptic textual tradition.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from .parser import TAG_RE, _scan_attrs


class SourceContextError(ValueError):
    """Pinned source bytes, original marker positions, or chapter do not match."""


@dataclass(frozen=True, slots=True)
class CopticSourceGapContext:
    source_marker_ordinal: int
    previous_verse: int
    current_verse: int
    missing_number_count: int
    words_since_prior_verse_marker: int
    source_metadata_keys: tuple[str, ...]
    editorial_greek_name_mentions: tuple[str, ...]
    status: str = "source_context_only"


# Deliberately just indicators of source/editorial metadata: a mention in a
# translator credit does not prove that this Coptic witness follows a Greek
# textual tradition. No source metadata *values* are emitted.
_GREEK_EDITION_WORDS = (
    "alexandrinus", "sinaiticus", "theodotion", "vaticanus",
)
_EDITORIAL_KEYS = frozenset(
    {"source", "source_info", "note", "translation", "Coptic_edition"}
)


def _positive(value: str | None) -> int | None:
    if value is None or not value.isascii() or not value.isdecimal():
        return None
    result = int(value)
    return result if result > 0 else None


def inspect_source_gap_context(
    raw: bytes,
    *,
    expected_sha256: str,
    expected_chapter: int,
    expected_events: Iterable[tuple[int, int, int]],
) -> tuple[CopticSourceGapContext, ...]:
    """Authenticate and measure every requested gap against exact TT tag order.

    expected_events are (1-based source verse marker ordinal, previous verse,
    current verse), *already source-byte qualified* by the #149 fixture. The
    returned counts measure original Coptic norm starts in the **preceding
    marker span**, not missing words or Greek textual omission.
    """
    if not isinstance(raw, bytes) or sha256(raw).hexdigest() != expected_sha256:
        raise SourceContextError("TT source byte fingerprint mismatch")
    if type(expected_chapter) is not int or expected_chapter < 1:
        raise SourceContextError("invalid expected source chapter")
    source = raw.decode("utf-8-sig")
    metadata_tag = TAG_RE.search(source)
    if metadata_tag is None or metadata_tag.group(2) != "meta" or metadata_tag.group(1):
        raise SourceContextError("missing leading TT metadata")
    metadata, _duplicates = _scan_attrs(metadata_tag.group(3), allow_duplicates=True)
    chapter = _positive(metadata.get("chapter"))
    if chapter != expected_chapter:
        raise SourceContextError("pinned chapter metadata contradicts research fixture")

    keys = tuple(sorted(metadata))
    editorial_values = " ".join(
        value.casefold()
        for key, value in metadata.items()
        if key in _EDITORIAL_KEYS
    )
    mentions = tuple(
        word for word in _GREEK_EDITION_WORDS if word in editorial_values
    )
    requests: dict[int, tuple[int, int]] = {}
    for item in expected_events:
        if (
            not isinstance(item, (tuple, list)) or len(item) != 3
            or any(type(x) is not int or x <= 0 for x in item)
        ):
            raise SourceContextError("invalid typed source marker evidence")
        marker, previous, current = item
        if marker in requests or current <= previous + 1:
            raise SourceContextError("duplicated marker or non-gap evidence")
        requests[marker] = (previous, current)
    if not requests:
        raise SourceContextError("source has no events to inspect")

    ordinal = 0
    word_starts = 0
    last_marker_word_starts = 0
    previous: int | None = None
    rows: list[CopticSourceGapContext] = []
    for tag in TAG_RE.finditer(source):
        if tag.group(1):
            continue
        name, attributes = tag.group(2), tag.group(3)
        if name == "norm":
            word_starts += 1
            continue
        if name == "chapter_n":
            attrs, _duplicates = _scan_attrs(attributes)
            new_chapter = _positive(attrs.get("chapter_n"))
            if new_chapter != chapter:
                chapter = new_chapter
                previous = None
                last_marker_word_starts = word_starts
            continue
        if name != "verse_n":
            continue
        ordinal += 1
        attrs, _duplicates = _scan_attrs(attributes)
        current = _positive(attrs.get("verse_n"))
        if ordinal in requests:
            prior_expected, current_expected = requests[ordinal]
            if (
                chapter != expected_chapter or previous != prior_expected
                or current != current_expected
            ):
                raise SourceContextError(
                    f"pinned source marker #{ordinal} no longer matches exact gap"
                )
            rows.append(CopticSourceGapContext(
                source_marker_ordinal=ordinal,
                previous_verse=prior_expected,
                current_verse=current_expected,
                missing_number_count=current_expected - prior_expected - 1,
                words_since_prior_verse_marker=word_starts - last_marker_word_starts,
                source_metadata_keys=keys,
                editorial_greek_name_mentions=mentions,
            ))
        previous = current
        last_marker_word_starts = word_starts

    if len(rows) != len(requests):
        raise SourceContextError("requested pinned verse marker missing from TT")
    return tuple(rows)
