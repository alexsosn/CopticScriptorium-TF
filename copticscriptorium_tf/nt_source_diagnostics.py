"""Lossless *diagnostic* inventory for uncertain Coptic SBL NT verse labels.

No remapping or normalization takes place here. Only bounded categorical tag
shapes, source record IDs, original occurrence ordinals and fixed reason codes
may leave the process; original Greek/apparatus/Coptic source text never does.
"""
from __future__ import annotations

from collections import Counter
import re
from typing import Iterable

from .nt_reference import CopticSblReference

_REASON_CODES = {
    "duplicate source identity or provenance metadata": "duplicate_source_identity",
    "unreviewed NT source or missing Greek provenance": "unreviewed_nt_source",
    "SBL occurrence has no fully enclosed Coptic word span": "no_complete_coptic_word_span",
    "contradictory source references in Coptic word span": "mixed_or_missing_word_markers",
    "missing or malformed source NT reference evidence": "missing_nt_reference_evidence",
    "contradictory NT book/chapter/verse evidence": "conflicting_nt_coordinates",
    "verse absent from pinned MorphGNT edition": "parent_edition_unavailable",
    "address unavailable in pinned Greek NT TF": "parent_verse_unavailable",
}
_CANDIDATE_REASON = "matching edition-qualified verse address; textual equivalence unverified"
_ALLOWED = frozenset({"ambiguous", "unresolved", "edition_unavailable",
                      "unclassified_source", "reference_candidate"})
_EDITOR = re.compile(r"(?:41N|46N) [1-9][0-9]*:[1-9][0-9]*\Z")
_CTS = re.compile(r"urn:cts:copticLit:nt\.[a-z0-9]+\.sahidica_ed:[1-9][0-9]*\.[1-9][0-9]*\Z")


def _shape(value: str | None) -> str:
    if value is None or value == "":
        return "missing"
    if not isinstance(value, str):
        raise ValueError("nontextual source reference shape")
    if _EDITOR.fullmatch(value):
        return "editor_reference"
    if _CTS.fullmatch(value):
        return "cts_verse"
    return "other"


class NonCandidateInventory:
    """Audit every source SBL occurrence, preserving physical duplication."""

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._original: Counter[str] = Counter()
        self._statuses: Counter[str] = Counter()
        self._reasons: Counter[str] = Counter()
        self._shape_groups: Counter[str] = Counter()
        self._by_record: dict[str, Counter[str]] = {}
        self._rows: list[dict[str, str | int]] = []

    def add(
        self, record: str, source: list[tuple[str, str]],
        resolved: Iterable[CopticSblReference],
    ) -> None:
        if not isinstance(record, str) or "/" not in record or ":" not in record:
            raise ValueError("invalid physical source ID")
        key = record.casefold()
        if key in self._seen:
            raise ValueError("duplicate physical source ID")
        self._seen.add(key)
        resolved = tuple(resolved)
        if not source or len(source) != len(resolved):
            raise ValueError("source annotation occurrence count mismatch")
        per_record = Counter()
        for ordinal, ((kind, literal), item) in enumerate(zip(source, resolved), start=1):
            if (kind not in {"sbl_greek", "sbl_apparatus"}
                or not isinstance(literal, str)
                or item.source_record_id != record
                or item.source_ordinal != ordinal
                or item.source_kind != kind):
                raise ValueError("source annotation occurrence identity/order mismatch")
            if item.status not in _ALLOWED:
                raise ValueError("unknown SBL candidate status")
            if item.status == "reference_candidate":
                if item.reason != _CANDIDATE_REASON:
                    raise ValueError("unknown SBL candidate reason")
            elif item.reason not in _REASON_CODES:
                raise ValueError("unknown noncandidate source reason")
            self._original[kind] += 1
            self._statuses[item.status] += 1
            per_record[item.status] += 1
            if item.status == "reference_candidate":
                continue
            reason_code = _REASON_CODES[item.reason]
            # The resolver collapses nonuniform word markers to None.
            # When the source span is conflicting, None means "unknown or
            # mixed", not proof that the original tag was absent.
            mixed = reason_code == "mixed_or_missing_word_markers"
            label_shape = ("indeterminate" if mixed and item.source_verse_vid is None
                           else _shape(item.source_verse_vid))
            vid_shape = ("indeterminate" if mixed and item.source_vid_n is None
                         else _shape(item.source_vid_n))
            greek_shape = _shape(literal) if kind == "sbl_greek" else "not_applicable"
            locus = ("complete_words" if item.source_word_ordinals
                     else "no_complete_word")
            row = {
                "source_record_id": record,
                "source_ordinal": ordinal,
                "kind": kind,
                "status": item.status,
                "reason_code": reason_code,
                "vid_n_shape": vid_shape,
                "verse_vid_shape": label_shape,
                "sbl_value_shape": greek_shape,
                "word_locus": locus,
            }
            self._rows.append(row)
            self._reasons[reason_code] += 1
            for field in ("vid_n_shape", "verse_vid_shape", "sbl_value_shape",
                          "word_locus"):
                self._shape_groups[f"{field}:{row[field]}"] += 1
        self._by_record[record] = per_record

    def finish(
        self, *, expected_statuses: dict[str, int], expected_annotated: int,
        expected_total: int,
    ) -> dict:
        if (len(self._seen) != expected_annotated
            or sum(self._statuses.values()) != expected_total
            or dict(self._statuses) != expected_statuses
            or len(self._rows) != (
                expected_total - self._statuses.get("reference_candidate", 0)
            )):
            raise ValueError("complete source diagnostic status count drift")
        return {
            "status": "pass",
            "scope": "Source reference label shape diagnostics; no source values or inferred verse fixes",
            "annotated_physical_records": len(self._seen),
            "source_annotations": sum(self._original.values()),
            "source_kinds": dict(sorted(self._original.items())),
            "statuses": dict(sorted(self._statuses.items())),
            "noncandidate_occurrences": len(self._rows),
            "reason_codes": dict(sorted(self._reasons.items())),
            "marker_shapes": dict(sorted(self._shape_groups.items())),
            "by_physical_record": {
                record: dict(sorted(counts.items()))
                for record, counts in sorted(self._by_record.items())
                if any(state != "reference_candidate" for state in counts)
            },
            "inventory": list(self._rows),
        }
