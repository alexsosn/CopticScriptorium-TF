"""Streaming metadata-only audit of pinned Coptic OT → real LXX verse addresses.

A shared book/chapter/verse *reference candidate* is NOT Greek–Coptic
textual/lexical equivalence. This module writes no TF parent IDs or source
text and retains only bounded physical source-identity examples.
"""
from __future__ import annotations

from collections import Counter
from typing import Callable

from .lxx_reference import resolve_coptic_lxx_references
from .model import DocumentModel
from .ot_inventory import classify_biblical_record

COPTIC_SOURCE_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
SCHEMA = "coptic_lxx_reference_coverage_v1"
REFERENCE_STATUSES = frozenset({
    "reference_candidate", "unresolved", "ambiguous", "unclassified_corpus",
})


def _smallest_examples(existing: list[str], value: str, *, limit: int = 3) -> None:
    """Deterministic top-N independent of archive traversal order."""
    if value not in existing:
        existing.append(value)
        existing.sort()
        del existing[limit:]


class CopticLxxCoverageAudit:
    """One source document at a time; no accumulated models or source text."""

    def __init__(
        self,
        *,
        source_commit: str,
        lookup: Callable[[str, int, int], int | None],
    ):
        if source_commit != COPTIC_SOURCE_PIN:
            raise ValueError("unsupported pinned Coptic source revision")
        self._source_commit = source_commit
        self._lookup = lookup
        self._seen: dict[str, str] = {}
        self._source_scopes: Counter[str] = Counter()
        self._refs: Counter[str] = Counter()
        self._words: Counter[str] = Counter()
        self._reasons: Counter[str] = Counter()
        self._families: dict[str, dict[str, object]] = {}
        self._books: dict[str, dict[str, object]] = {}
        self._works: dict[str, dict[str, object]] = {}
        self._total_words = 0
        self._ot_words = 0
        self._midword_events = 0

    @staticmethod
    def _new_group() -> dict[str, object]:
        return {
            "source_records": 0,
            "source_word_slots": 0,
            "scope_counts": Counter(),
            "reference_statuses": Counter(),
            "word_statuses": Counter(),
            "examples": [],
        }

    @staticmethod
    def _update_group(
        group: dict[str, object],
        document: DocumentModel,
        *,
        scope: str,
        statuses: Counter[str],
        words: Counter[str],
    ) -> None:
        group["source_records"] += 1
        group["source_word_slots"] += len(document.words)
        group["scope_counts"][scope] += 1
        group["reference_statuses"].update(statuses)
        group["word_statuses"].update(words)
        _smallest_examples(group["examples"], document.source_record_id)

    def add(self, document: DocumentModel) -> None:
        if document.upstream_repository != "CopticScriptorium/corpora" or (
            document.upstream_commit != self._source_commit
        ):
            raise ValueError("source revision/repository mismatch")
        # Match parse_source_tree's global casefold collision guard, not
        # just Python's case-sensitive string membership.
        key = document.source_record_id.casefold()
        previous = self._seen.get(key)
        if previous is not None:
            raise ValueError(
                f"duplicate physical source record: {previous!r} versus "
                f"{document.source_record_id!r}"
            )
        self._seen[key] = document.source_record_id
        evidence = classify_biblical_record(document.corpus, document.metadata)
        self._source_scopes[evidence.status] += 1
        self._total_words += len(document.words)
        self._midword_events += sum(
            event.kind in {"verse_n_marker", "vid_n_marker", "verse_vid_marker"}
            for event in document.layout_events
        )

        statuses: Counter[str] = Counter()
        words: Counter[str] = Counter()
        if evidence.status == "ot_candidate":
            self._ot_words += len(document.words)
            refs = resolve_coptic_lxx_references(document, lookup=self._lookup)
            ordinals = [
                ordinal for ref in refs for ordinal in ref.source_word_ordinals
            ]
            if sorted(ordinals) != list(range(1, len(document.words) + 1)):
                raise ValueError(
                    f"source word coverage is not an exact partition: {document.source_record_id}"
                )
            for ref in refs:
                if ref.status not in REFERENCE_STATUSES:
                    raise ValueError(f"unknown LXX mapping status {ref.status!r}")
                if ref.status == "reference_candidate":
                    if ref.lxx_node is None or ref.shared_id is None:
                        raise ValueError("positive reference candidate lacks a verified LXX node")
                elif ref.lxx_node is not None or ref.shared_id is not None:
                    raise ValueError("unresolved/ambiguous verse invented a Greek correspondence")
                statuses[ref.status] += 1
                words[ref.status] += len(ref.source_word_ordinals)
                self._reasons[ref.reason] += 1
                book_label = ref.lxx_book or "unclassified"
                book_row = self._books.setdefault(book_label, {
                    "reference_statuses": Counter(),
                    "word_statuses": Counter(),
                    "examples": [],
                })
                # A single physical document may span several Greek references.
                book_row["reference_statuses"][ref.status] += 1
                book_row["word_statuses"][ref.status] += len(ref.source_word_ordinals)
                _smallest_examples(book_row["examples"], document.source_record_id)
            self._refs.update(statuses)
            self._words.update(words)

        family = self._families.setdefault(document.corpus, self._new_group())
        self._update_group(
            family, document, scope=evidence.status, statuses=statuses, words=words
        )
        work_key = (
            f"{evidence.cts_scope}.{evidence.cts_work}"
            if evidence.cts_scope and evidence.cts_work
            else "<missing_cts_work>"
        )
        work = self._works.setdefault(work_key, self._new_group())
        self._update_group(
            work, document, scope=evidence.status, statuses=statuses, words=words
        )

    def report(self) -> dict[str, object]:
        def sorted_counts(counter: Counter[str]) -> dict[str, int]:
            return dict(sorted(counter.items()))

        def serialize_row(row: dict[str, object]) -> dict[str, object]:
            return {
                key: sorted_counts(value) if isinstance(value, Counter) else value
                for key, value in sorted(row.items())
            }

        if sum(self._source_scopes.values()) != len(self._seen):
            raise ValueError("unbalanced physical source scope classification")
        if sum(self._words.values()) != self._ot_words:
            raise ValueError("unbalanced Coptic OT word status accounting")

        return {
            "schema": SCHEMA,
            "coptic_source_commit": self._source_commit,
            "lxx_parent": "CenterBLC/LXX:1935:v1.0.1",
            "lxx_parent_commit": "f32a98eddf7eb239aa73ab863d70381e416d5076",
            "totals": {
                "source_records": len(self._seen),
                "source_word_slots": self._total_words,
                "ot_candidate_word_slots": self._ot_words,
                "verse_position_events": self._midword_events,
                "ot_reference_groups": sum(self._refs.values()),
            },
            "source_scopes": sorted_counts(self._source_scopes),
            "ot_reference_statuses": sorted_counts(self._refs),
            "ot_word_statuses": sorted_counts(self._words),
            "ot_reference_reason_counts": sorted_counts(self._reasons),
            "families": {
                key: serialize_row(row) for key, row in sorted(self._families.items())
            },
            "cts_works": {
                key: serialize_row(row) for key, row in sorted(self._works.items())
            },
            "candidate_lxx_books": {
                key: serialize_row(row) for key, row in sorted(self._books.items())
            },
            "interpretation": (
                "Reference address candidates only; Coptic/LXX textual equivalence, "
                "versification and token alignment NOT verified"
            ),
        }
