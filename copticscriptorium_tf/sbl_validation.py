"""Release-gate SBL source -> full native TF conservation validation.

The report is source-free. No Greek text or copyrighted Coptic corpus is
exported. This is deliberately independent of the writer's GraphNode model:
source TT literals/offsets are compared to *reloaded* TF feature values.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import gc
import json
from pathlib import Path
from typing import Any

from .model import SblAnnotation
from .parser import parse_tt_record

PINNED_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
EXPECTED_RECORDS = 2628
EXPECTED_WORD_SLOTS = 2394354
EXPECTED_SBL = {"sbl_greek": 1652, "sbl_apparatus": 1095}
FIELDS = (
    "source_ordinal", "value", "sbl_verse_n",
    "start_word_ordinal", "start_char", "start_after_word_ordinal",
    "end_word_ordinal", "end_char", "end_after_word_ordinal",
)
TF_FEATURES = " ".join(("source_record_id", *FIELDS, "render_mode"))
KINDS = ("sbl_greek", "sbl_apparatus")


def compare_occurrence(
    expected: SblAnnotation, native: dict[str, Any], *,
    first_slot: int, word_count: int | None = None,
) -> None:
    """Fail on ANY source-literal, scoped-boundary or slot-locus drift.

    No Greek text appears in an exception message, even for value mismatches.
    """
    expected_fields = {
        "source_ordinal": expected.ordinal,
        "value": expected.value,
        "sbl_verse_n": expected.source_verse_n,
        "start_word_ordinal": expected.start_word_ordinal,
        "start_char": expected.start_char,
        "start_after_word_ordinal": expected.start_after_word_ordinal,
        "end_word_ordinal": expected.end_word_ordinal,
        "end_char": expected.end_char,
        "end_after_word_ordinal": expected.end_after_word_ordinal,
    }
    if native.get("kind") != expected.kind:
        raise ValueError("SBL occurrence kind mismatch")
    for key, value in expected_fields.items():
        if native.get(key) != value:
            raise ValueError(f"SBL occurrence {key} mismatch")
    is_span = bool(expected.word_ordinals)
    mode = "sbl_span" if is_span else "sbl_anchor"
    if native.get("render_mode") != mode:
        raise ValueError("SBL occurrence render_mode mismatch")
    actual_slots = tuple(native.get("slots", ()))
    if is_span:
        wanted = tuple(first_slot + n - 1 for n in expected.word_ordinals)
        if actual_slots != wanted:
            raise ValueError("SBL occurrence slots mismatch")
    else:
        if word_count is None:
            word_count = max(1, expected.start_after_word_ordinal + 1)
        anchor = (expected.start_word_ordinal if expected.start_word_ordinal is not None
                  else min(word_count, expected.start_after_word_ordinal + 1))
        if actual_slots != (first_slot + anchor - 1,):
            raise ValueError("SBL occurrence slots anchor mismatch")


def _native_sbl_nodes(api) -> dict[tuple[str, str, int], dict]:
    """Read all SBL nodes once; fail closed on collisions/missing scalar fields."""
    result = {}
    for kind in KINDS:
        for node in api.F.otype.s(kind):
            record = api.F.source_record_id.v(node)
            ordinal = api.F.source_ordinal.v(node)
            if not isinstance(record, str) or not isinstance(ordinal, int):
                raise ValueError(f"SBL native {kind} node has missing source identity")
            key = (record, kind, ordinal)
            if key in result:
                raise ValueError("duplicate native SBL source occurrence key")
            obj = {name: getattr(api.F, name).v(node) for name in FIELDS}
            obj["kind"] = kind
            obj["render_mode"] = api.F.render_mode.v(node)
            obj["slots"] = tuple(api.L.d(node, otype="word"))
            result[key] = obj
    return result


def _document_slot_windows(api) -> dict[str, tuple[int, int]]:
    result = {}
    for node in api.F.otype.s("document"):
        record = api.F.source_record_id.v(node)
        if record in result:
            raise ValueError("duplicate native physical document")
        slots = api.L.d(node, otype="word")
        if not slots or slots[-1] - slots[0] + 1 != len(slots):
            raise ValueError("noncontiguous native document word slots")
        result[record] = (slots[0], len(slots))
    return result


def compare_source_to_tf(root: Path, tf_dir: Path) -> dict:
    """Independently scan every physical TT record, including archive members."""
    from tf.fabric import Fabric
    from .sbl_source_census import records, expected_sbl

    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(TF_FEATURES, silent="deep")
    if not api:
        raise ValueError("full native Text-Fabric SBL feature reload failed")
    if api.F.otype.maxSlot != EXPECTED_WORD_SLOTS:
        raise ValueError("full corpus word-slot count drift")
    windows = _document_slot_windows(api)
    observed = _native_sbl_nodes(api)
    counts = Counter()
    modes = Counter()
    visited = set()
    physical = 0
    annotated = 0
    digest = sha256()
    for record, path, raw, packaging in records(root):
        physical += 1
        window = windows.get(record)
        if window is None:
            raise ValueError(f"source record missing from native TF: {record}")
        source_literals = expected_sbl(raw)
        if not source_literals:
            continue
        annotated += 1
        parsed = parse_tt_record(
            raw, source_record_id=record, source_path=path, packaging=packaging,
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PINNED_COMMIT,
        )
        if [(a.kind, a.value) for a in parsed.sbl_annotations] != source_literals:
            raise ValueError(f"source/model SBL discrepancy at {record}")
        for a in parsed.sbl_annotations:
            key = (record, a.kind, a.ordinal)
            if key in visited:
                raise ValueError("duplicate source annotation identity")
            visited.add(key)
            row = observed.get(key)
            if row is None:
                raise ValueError(f"native TF omitted SBL occurrence at {record} #{a.ordinal}")
            compare_occurrence(a, row, first_slot=window[0], word_count=window[1])
            counts[a.kind] += 1
            modes[row["render_mode"]] += 1
            # Digest includes source text evidence but discloses no corpus contents.
            digest.update(json.dumps(
                (record, a.kind, a.ordinal, a.value, a.source_verse_n,
                 a.word_ordinals, a.start_word_ordinal, a.start_char,
                 a.end_word_ordinal, a.end_char),
                ensure_ascii=False,
            ).encode("utf-8"))
            digest.update(b"\n")
    if physical != EXPECTED_RECORDS or len(windows) != EXPECTED_RECORDS:
        raise ValueError("pinned physical document count mismatch")
    if set(observed) != visited:
        raise ValueError("native TF contains unpaired or extra SBL source occurrences")
    if dict(counts) != EXPECTED_SBL:
        raise ValueError("SBL full-source occurrence count drift")
    if modes != {"sbl_span": 2739, "sbl_anchor": 8}:
        raise ValueError("SBL span/anchor classification drift")
    return {
        "status": "pass",
        "upstream_commit": PINNED_COMMIT,
        "physical_records": physical,
        "annotated_physical_records": annotated,
        "native_document_nodes": len(windows),
        "native_word_slots": api.F.otype.maxSlot,
        "source_native_sbl_occurrences": dict(sorted(counts.items())),
        "source_native_locus_classes": dict(sorted(modes.items())),
        "sbl_source_value_sha256": digest.hexdigest(),
        "scope": "Exact pinned source TT/ZIP to complete regenerated native TF; no word-level Greek alignment",
    }
