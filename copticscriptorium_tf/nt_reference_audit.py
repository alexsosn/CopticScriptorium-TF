"""Coptic-owned fail-closed census of edition-qualified Greek NT candidates.

Every original SBL source annotation must have exactly one resolver disposition.
Never copy Greek/Coptic lexical values into reports, or write a Greek TF ID into
a Coptic TF feature. This module is independent of the TF converter/writer.
"""
from __future__ import annotations

from collections import Counter
from typing import Callable, Iterable

from .nt_reference import CopticSblReference, GREEK_NT_EDITION

_STATUSES = frozenset((
    "reference_candidate", "ambiguous", "unresolved",
    "edition_unavailable", "unclassified_source",
))


class CandidateAudit:
    def __init__(self) -> None:
        self.seen: set[str] = set()
        self.physical = 0
        self.annotated = 0
        self.kinds: Counter[str] = Counter()
        self.statuses: Counter[str] = Counter()
        self.by_corpus: dict[str, Counter[str]] = {}
        self.unresolved_examples: list[dict[str, str | int]] = []
        self.unique_parent_addresses: set[str] = set()

    def _enter(self, record: str) -> str:
        if not record or "/" not in record or ":" not in record:
            raise ValueError("invalid physical source record ID")
        normalized = record.casefold()
        if normalized in self.seen:
            raise ValueError("duplicate physical source record")
        self.seen.add(normalized)
        self.physical += 1
        return record.split("/", 1)[0]

    def add_unannotated(self, record: str) -> None:
        self._enter(record)

    def add(
        self,
        record: str,
        source: list[tuple[str, str]],
        resolved: Iterable[CopticSblReference],
        *,
        reverse_lookup: Callable[[int], tuple[str, int, int] | None],
    ) -> None:
        if not source:
            raise ValueError("annotated audit expects at least one source occurrence")
        corpus = self._enter(record)
        occurrences = tuple(resolved)
        if len(source) != len(occurrences):
            raise ValueError("source/resolver occurrence count mismatch")
        self.annotated += 1
        by_corpus = self.by_corpus.setdefault(corpus, Counter())
        for ordinal, ((kind, _literal), item) in enumerate(
            zip(source, occurrences), start=1
        ):
            if item.source_record_id != record or item.source_kind != kind or item.source_ordinal != ordinal:
                raise ValueError("wrong physical source occurrence identity/order")
            if item.status not in _STATUSES:
                raise ValueError("unknown candidate resolution status")
            self.kinds[kind] += 1
            self.statuses[item.status] += 1
            by_corpus[item.status] += 1
            if item.status == "reference_candidate":
                if (
                    not isinstance(item.target_node, int)
                    or isinstance(item.target_node, bool)
                    or item.target_node < 1
                ):
                    raise ValueError("invalid Greek parent candidate node")
                expected = (
                    f"{GREEK_NT_EDITION}:{item.target_book}:"
                    f"{item.target_chapter}:{item.target_verse}"
                )
                if item.shared_id != expected:
                    raise ValueError("wrong edition-qualified source reference")
                if reverse_lookup(item.target_node) != (
                    item.target_book, item.target_chapter, item.target_verse
                ):
                    raise ValueError("Greek parent reverse section mismatch")
                self.unique_parent_addresses.add(item.shared_id)
            else:
                if item.target_node is not None or item.shared_id is not None:
                    raise ValueError("unresolved annotation contains foreign Greek target")
                if len(self.unresolved_examples) < 24:
                    self.unresolved_examples.append({
                        "source_record_id": record, "source_ordinal": ordinal,
                        "kind": kind, "status": item.status, "reason": item.reason,
                    })

    def finish(
        self,
        *,
        expected_physical: int,
        expected_annotated: int,
        expected_kinds: dict[str, int],
    ) -> dict:
        if (
            self.physical != expected_physical
            or self.annotated != expected_annotated
            or dict(self.kinds) != expected_kinds
            or sum(self.statuses.values()) != sum(expected_kinds.values())
        ):
            raise ValueError("pinned SBL source/resolver count drift")
        return {
            "status": "pass",
            "scope": "Coptic-owned verse-address candidates only; no Greek word alignment",
            "edition": GREEK_NT_EDITION,
            "physical_records": self.physical,
            "annotated_records": self.annotated,
            "source_annotation_kinds": dict(sorted(self.kinds.items())),
            "statuses": dict(sorted(self.statuses.items())),
            "by_physical_corpus": {
                corpus: dict(sorted(counts.items()))
                for corpus, counts in sorted(self.by_corpus.items())
            },
            "distinct_candidate_verse_addresses": len(self.unique_parent_addresses),
            "noncandidate_examples": self.unresolved_examples,
        }
