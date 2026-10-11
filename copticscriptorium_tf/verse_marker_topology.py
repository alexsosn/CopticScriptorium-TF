"""Bounded, source-literal Coptic verse-marker topology audit (#105).

Source `verse_n` occurrences need not equal resolved word-group counts:
consecutive identical labels and zero-word markers can collapse in an ordinary
word-scoped reference resolver. These are *diagnostics*, not Greek alignment.
No source text, Coptic lexical forms or foreign TF node IDs leave this audit.
"""
from __future__ import annotations

from collections import Counter
import re

from .parser import TAG_RE

_NUMBER = re.compile(r'(?:^|\s)verse_n\s*=\s*"([^"]*)"')
_CATEGORIES = (
    "duplicate_same_number",
    "nonmonotonic",
    "gapped",
    "no_word_start_between_markers",
    "missing_or_nonpositive_literal",
)


def _positive_source_verse(literal: str | None) -> int | None:
    if literal is None or not literal.isascii() or not literal.isdecimal():
        return None
    n = int(literal)
    return n if n > 0 else None


class VerseMarkerTopologyAudit:
    """Track actual opening source tags with deterministic bounded examples."""

    def __init__(self, *, example_limit: int = 3) -> None:
        if example_limit < 1:
            raise ValueError("example_limit must be positive")
        self._limit = example_limit
        self._counts: Counter[str] = Counter()
        self._examples: dict[str, list[str]] = {}
        self._records = 0
        self._records_with_marker = 0
        self._opening_markers = 0

    def _observe(self, category: str, source_record_id: str) -> None:
        self._counts[category] += 1
        examples = self._examples.setdefault(category, [])
        if source_record_id not in examples:
            examples.append(source_record_id)
            examples.sort()
            del examples[self._limit:]

    def add(self, source_text: str, source_record_id: str) -> None:
        if not isinstance(source_text, str) or not source_record_id:
            raise ValueError("source event audit requires text and source record identity")
        self._records += 1
        n_markers = 0
        previous: int | None = None
        pending_verse = False
        words_since_marker = 0

        for tag in TAG_RE.finditer(source_text):
            closing, name, attributes = tag.group(1), tag.group(2), tag.group(3)
            if closing:
                continue
            if name == "norm":
                if pending_verse:
                    words_since_marker += 1
                continue
            if name != "verse_n":
                continue
            n_markers += 1
            self._opening_markers += 1
            if pending_verse and words_since_marker == 0:
                self._observe("no_word_start_between_markers", source_record_id)
            words_since_marker = 0
            pending_verse = True

            literal_match = _NUMBER.search(attributes)
            current = _positive_source_verse(
                literal_match.group(1) if literal_match else None
            )
            if current is None:
                self._observe("missing_or_nonpositive_literal", source_record_id)
                previous = None
                continue
            if previous is not None:
                if current == previous:
                    self._observe("duplicate_same_number", source_record_id)
                elif current < previous:
                    self._observe("nonmonotonic", source_record_id)
                elif current > previous + 1:
                    self._observe("gapped", source_record_id)
            previous = current

        if pending_verse and words_since_marker == 0:
            self._observe("no_word_start_between_markers", source_record_id)
        if n_markers:
            self._records_with_marker += 1

    def report(self) -> dict[str, object]:
        return {
            "source_records": self._records,
            "source_records_with_verse_n": self._records_with_marker,
            "opening_verse_n_tags": self._opening_markers,
            "categories": {
                key: self._counts[key] for key in _CATEGORIES if self._counts[key]
            },
            "examples": {
                key: list(sorted(self._examples[key]))
                for key in _CATEGORIES if key in self._examples
            },
            "interpretation": (
                "source marker shape only; no intervening norm start may reflect an internal-word boundary; repeated labels, gaps and decreases "
                "are not proof of erroneous Coptic or LXX versification"
            ),
        }
