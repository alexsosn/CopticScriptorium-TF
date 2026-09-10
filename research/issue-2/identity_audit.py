"""Corpus-wide identity/overlap audit for Coptic Scriptorium TT sources.

This is research tooling for issue #2, not production converter code. It keeps
physical source identity, scholarly CTS identity, text identity, linguistic-analysis
identity, documented collection overlap, and redundancy/witness relations separate
so later Text-Fabric design does not deduplicate records from one convenient key.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
from typing import Any, Iterator
import zipfile

META_ATTRIBUTE_RE = re.compile(
    r'\s+([A-Za-z_][A-Za-z0-9_.:-]*)\s*=\s*"([^"]*)"'
)
TAG_ATTRIBUTE_RE = META_ATTRIBUTE_RE
NORM_TAG_RE = re.compile(r'<norm\b((?:[^">]|"[^"]*")*)>', re.DOTALL)
ORIG_TAG_RE = re.compile(r'<orig\b((?:[^">]|"[^"]*")*)>', re.DOTALL)
CTS_URN_RE = re.compile(r"urn:cts:[^\s]+")

ENRICHMENT_PATTERNS: dict[str, re.Pattern[str]] = {
    "translation": re.compile(r"<translation\b"),
    "arabic_translation": re.compile(r"<(?:arabic|arabic_translation)\b"),
    "entity": re.compile(r"<entity\b"),
    "entity_identity": re.compile(r"<entity\b[^>]*\bidentity\s*="),
    "page": re.compile(r"<(?:pb|pb_[A-Za-z0-9_]+)\b"),
    "column": re.compile(r"<(?:cb|cb_[A-Za-z0-9_]+)\b"),
    "line": re.compile(r"<(?:lb|lb_[A-Za-z0-9_]+)\b"),
}

CLASS_SEVERITY = {
    "byte_identical": 0,
    "core_identical_source_variant": 1,
    "alternate_analysis": 2,
    "textual_divergence": 3,
}

# These relations come from the pinned upstream README. They are deliberately
# finite and dataset-specific: similar CTS spelling is not enough to infer an
# overlap relation for any other corpus.
DOCUMENTED_COLLECTION_OVERLAP_SPECS = (
    {
        "left_dataset": "sahidica.mark/sahidica.mark",
        "left_prefix": "Mark_",
        "right_dataset": "sahidica.nt/sahidica.nt",
        "right_prefix": "41_Mark_",
        "chapters": range(1, 17),
    },
    {
        "left_dataset": "sahidica.1corinthians/sahidica.1corinthians",
        "left_prefix": "1Cor_",
        "right_dataset": "sahidica.nt/sahidica.nt",
        "right_prefix": "46_1_Corinthians_",
        "chapters": range(1, 17),
    },
    {
        "left_dataset": "sahidic.ruth/sahidic.ruth",
        "left_prefix": "Ruth_",
        "right_dataset": "sahidic.ot/sahidic.ot",
        "right_prefix": "08_Ruth_",
        "chapters": range(1, 5),
    },
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash_json(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256_bytes(payload)


def _scan_attributes(fragment: str) -> dict[str, str]:
    position = 0
    attrs: dict[str, str] = {}
    while position < len(fragment):
        if fragment[position:].strip() == "":
            break
        match = TAG_ATTRIBUTE_RE.match(fragment, position)
        if match is None:
            raise ValueError(f"malformed tag attributes near offset {position}")
        name = match.group(1)
        value = html.unescape(match.group(2))
        if name in attrs:
            raise ValueError(f"duplicate token attribute {name!r}")
        attrs[name] = value
        position = match.end()
    return attrs


def _scan_meta_line(line: str) -> dict[str, Any]:
    stripped = line.strip().lstrip("\ufeff")
    if not stripped.startswith("<meta") or not stripped.endswith(">"):
        raise ValueError("not a complete <meta ...> start tag")
    body_end = -2 if stripped.endswith("/>") else -1
    body = stripped[len("<meta") : body_end]
    position = 0
    pairs: list[tuple[str, str]] = []
    while position < len(body):
        if body[position:].strip() == "":
            break
        match = META_ATTRIBUTE_RE.match(body, position)
        if match is None:
            raise ValueError(f"malformed meta attribute syntax near offset {position}")
        pairs.append((match.group(1), html.unescape(match.group(2))))
        position = match.end()

    values: dict[str, list[str]] = {}
    attrs: dict[str, str] = {}
    for name, value in pairs:
        values.setdefault(name, []).append(value)
        attrs.setdefault(name, value)
    duplicates = {
        name: entries
        for name, entries in sorted(values.items())
        if len(entries) > 1
    }
    return {"attributes": attrs, "duplicates": duplicates, "values": values}


def _first_meta_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip().lstrip("\ufeff")
        if stripped.startswith("<meta"):
            return stripped
        if stripped:
            return None
    return None


def _tt_tokens(text: str) -> list[dict[str, Any]]:
    raw_tokens: list[dict[str, str]] = []
    id_to_position: dict[str, int] = {}
    for position, match in enumerate(NORM_TAG_RE.finditer(text), start=1):
        attrs = _scan_attributes(match.group(1))
        xml_id = attrs.get("xml:id")
        if xml_id:
            if xml_id in id_to_position:
                raise ValueError(f"duplicate TT token xml:id {xml_id!r}")
            id_to_position[xml_id] = position
        raw_tokens.append(attrs)

    tokens: list[dict[str, Any]] = []
    for attrs in raw_tokens:
        raw_head = attrs.get("head")
        if raw_head:
            target = raw_head[1:] if raw_head.startswith("#") else raw_head
            if target not in id_to_position:
                raise ValueError(f"unresolved TT dependency head {raw_head!r}")
            head: int | None = id_to_position[target]
        elif attrs.get("func") == "root":
            head = 0
        else:
            head = None
        tokens.append(
            {
                "norm": attrs.get("norm"),
                "lemma": attrs.get("lemma"),
                "pos": attrs.get("pos"),
                "func": attrs.get("func"),
                "head": head,
            }
        )
    return tokens


def _orig_sequence(text: str) -> list[str | None]:
    return [
        _scan_attributes(match.group(1)).get("orig")
        for match in ORIG_TAG_RE.finditer(text)
    ]


def _enrichment(text: str) -> dict[str, int]:
    return {
        key: len(pattern.findall(text))
        for key, pattern in sorted(ENRICHMENT_PATTERNS.items())
    }


def _record_from_bytes(
    *,
    dataset: str,
    record: str,
    source: str,
    packaging: str,
    raw: bytes,
) -> dict[str, Any]:
    text = raw.decode("utf-8")
    meta_line = _first_meta_line(text)
    malformed_identity_value: str | None = None
    if meta_line is None:
        attrs: dict[str, str] = {}
        duplicate_meta: dict[str, list[str]] = {}
        metadata_error: str | None = "missing_meta"
        scholarly_id: str | None = None
        identity_status = "missing_document_cts_urn"
        identity_conflict_values: list[str] = []
    else:
        scanned = _scan_meta_line(meta_line)
        attrs = scanned["attributes"]
        duplicate_meta = scanned["duplicates"]
        metadata_error = None
        cts_values = scanned["values"].get("document_cts_urn", [])
        distinct_cts = list(dict.fromkeys(cts_values))
        if not distinct_cts:
            scholarly_id = None
            identity_status = "missing_document_cts_urn"
            identity_conflict_values = []
        elif len(distinct_cts) > 1:
            scholarly_id = None
            identity_status = "conflicting_document_cts_urn"
            identity_conflict_values = list(cts_values)
        elif CTS_URN_RE.fullmatch(distinct_cts[0]) is None:
            scholarly_id = None
            identity_status = "malformed_document_cts_urn"
            identity_conflict_values = []
            malformed_identity_value = distinct_cts[0]
        else:
            scholarly_id = distinct_cts[0]
            identity_status = "usable"
            identity_conflict_values = []

    tokens = _tt_tokens(text)
    normalized = [token["norm"] for token in tokens]
    original = _orig_sequence(text)
    analysis = [
        {
            "norm": token["norm"],
            "lemma": token["lemma"],
            "pos": token["pos"],
            "func": token["func"],
            "head": token["head"],
        }
        for token in tokens
    ]
    source_record_id = f"{dataset}:{record}"
    return {
        "source_record_id": source_record_id,
        "dataset": dataset,
        "record": record,
        "source": source,
        "packaging": packaging,
        "raw_sha256": _sha256_bytes(raw),
        "raw_size": len(raw),
        "scholarly_id": scholarly_id,
        "identity_status": identity_status,
        "identity_conflict_values": identity_conflict_values,
        "malformed_identity_value": malformed_identity_value,
        "metadata_corpus": attrs.get("corpus"),
        "title": attrs.get("title"),
        "redundant": attrs.get("redundant"),
        "witness": attrs.get("witness"),
        "segmentation_quality": attrs.get("segmentation"),
        "tagging_quality": attrs.get("tagging"),
        "parsing_quality": attrs.get("parsing"),
        "entities_quality": attrs.get("entities"),
        "identities_quality": attrs.get("identities"),
        "normalized_token_count": len(normalized),
        "original_segment_count": len(original),
        "normalized_text_sha256": _hash_json(normalized),
        "original_text_sha256": _hash_json(original),
        "analysis_sha256": _hash_json(analysis),
        "enrichment": _enrichment(text),
        "metadata_error": metadata_error,
        "duplicate_meta_attributes": duplicate_meta,
    }


def _iter_direct_records(root: Path) -> Iterator[dict[str, Any]]:
    for directory in sorted(
        (path for path in root.rglob("*_TT") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        relative = directory.relative_to(root)
        if len(relative.parts) != 2 or not relative.parts[1].endswith("_TT"):
            continue
        corpus = relative.parts[0]
        dataset_name = relative.parts[1][:-3]
        dataset = f"{corpus}/{dataset_name}"
        for path in sorted(directory.rglob("*.tt"), key=lambda item: item.as_posix()):
            logical = path.relative_to(directory).as_posix()
            record = logical[:-3]
            yield _record_from_bytes(
                dataset=dataset,
                record=record,
                source=path.relative_to(root).as_posix(),
                packaging="directory",
                raw=path.read_bytes(),
            )


def _iter_archive_records(root: Path) -> Iterator[dict[str, Any]]:
    for archive_path in sorted(root.rglob("*_TT.zip"), key=lambda path: path.as_posix()):
        relative = archive_path.relative_to(root)
        if len(relative.parts) != 2 or not relative.parts[1].endswith("_TT.zip"):
            continue
        corpus = relative.parts[0]
        dataset_name = relative.parts[1][:-7]
        dataset = f"{corpus}/{dataset_name}"
        expected_prefix = f"{dataset_name}_TT/"
        with zipfile.ZipFile(archive_path) as archive:
            members = sorted(
                member
                for member in archive.namelist()
                if not member.endswith("/") and member.lower().endswith(".tt")
            )
            for member in members:
                if "/" not in member:
                    logical = member
                elif member.startswith(expected_prefix):
                    logical = member[len(expected_prefix) :]
                    if not logical:
                        raise ValueError(
                            f"empty TT archive record path in {relative.as_posix()}: {member!r}"
                        )
                else:
                    raise ValueError(
                        f"unsupported TT archive member layout in {relative.as_posix()}: {member!r}"
                    )
                record = logical[:-3]
                yield _record_from_bytes(
                    dataset=dataset,
                    record=record,
                    source=f"{relative.as_posix()}!/{member}",
                    packaging="archive",
                    raw=archive.read(member),
                )


def iter_tt_records(root: Path | str) -> Iterator[dict[str, Any]]:
    root_path = Path(root)
    yield from _iter_direct_records(root_path)
    yield from _iter_archive_records(root_path)


def _classify_pair(left: dict[str, Any], right: dict[str, Any]) -> str:
    if left["raw_sha256"] == right["raw_sha256"]:
        return "byte_identical"
    if (
        left["normalized_text_sha256"] != right["normalized_text_sha256"]
        or left["original_text_sha256"] != right["original_text_sha256"]
    ):
        return "textual_divergence"
    if left["analysis_sha256"] != right["analysis_sha256"]:
        return "alternate_analysis"
    return "core_identical_source_variant"


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "source_record_id",
        "dataset",
        "record",
        "source",
        "packaging",
        "raw_sha256",
        "raw_size",
        "scholarly_id",
        "identity_status",
        "identity_conflict_values",
        "malformed_identity_value",
        "metadata_corpus",
        "title",
        "redundant",
        "witness",
        "segmentation_quality",
        "tagging_quality",
        "parsing_quality",
        "entities_quality",
        "identities_quality",
        "normalized_token_count",
        "original_segment_count",
        "normalized_text_sha256",
        "original_text_sha256",
        "analysis_sha256",
        "enrichment",
        "metadata_error",
        "duplicate_meta_attributes",
    )
    return {key: record[key] for key in keys}


def _documented_collection_overlaps(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, int]]:
    by_source_id = {record["source_record_id"]: record for record in records}
    overlaps: list[dict[str, Any]] = []
    unmatched: list[dict[str, str]] = []
    class_counts: Counter[str] = Counter()

    for spec in DOCUMENTED_COLLECTION_OVERLAP_SPECS:
        for chapter in spec["chapters"]:
            chapter_text = f"{chapter:02d}"
            left_id = (
                f"{spec['left_dataset']}:"
                f"{spec['left_prefix']}{chapter_text}"
            )
            right_id = (
                f"{spec['right_dataset']}:"
                f"{spec['right_prefix']}{chapter_text}"
            )
            left = by_source_id.get(left_id)
            right = by_source_id.get(right_id)
            if left is None and right is None:
                continue
            if left is None:
                unmatched.append(
                    {
                        "expected_left": left_id,
                        "right": right_id,
                        "missing_side": "left",
                    }
                )
                continue
            if right is None:
                unmatched.append(
                    {
                        "left": left_id,
                        "expected_right": right_id,
                        "missing_side": "right",
                    }
                )
                continue

            classification = _classify_pair(left, right)
            class_counts[classification] += 1
            overlaps.append(
                {
                    "relation": "book_aggregate",
                    "left": left_id,
                    "right": right_id,
                    "left_scholarly_id": left["scholarly_id"],
                    "right_scholarly_id": right["scholarly_id"],
                    "same_scholarly_id": bool(
                        left["scholarly_id"]
                        and right["scholarly_id"]
                        and left["scholarly_id"] == right["scholarly_id"]
                    ),
                    "classification": classification,
                }
            )

    return (
        sorted(overlaps, key=lambda item: (item["left"], item["right"])),
        sorted(
            unmatched,
            key=lambda item: (
                item.get("left", item.get("expected_left", "")),
                item.get("right", item.get("expected_right", "")),
            ),
        ),
        {key: class_counts[key] for key in sorted(CLASS_SEVERITY)},
    )


def _extract_witness_cts_targets(witness: str) -> list[str]:
    targets: list[str] = []
    for match in CTS_URN_RE.finditer(witness):
        target = match.group(0).rstrip(".,;!?)]}")
        if target and target not in targets:
            targets.append(target)
    return targets


def audit_upstream(root: Path | str) -> dict[str, Any]:
    records = sorted(iter_tt_records(root), key=lambda record: record["source_record_id"])

    address_index: dict[str, str] = {}
    for record in records:
        literal = record["source_record_id"]
        technical = literal.casefold()
        previous = address_index.get(technical)
        if previous is not None and previous != literal:
            raise ValueError(
                f"source-record case-insensitive collision: {previous!r} versus {literal!r}"
            )
        if previous is not None:
            raise ValueError(f"duplicate source-record identity: {literal!r}")
        address_index[technical] = literal

    by_scholarly: dict[str, list[dict[str, Any]]] = {}
    missing_scholarly: list[dict[str, Any]] = []
    for record in records:
        scholarly = record["scholarly_id"]
        if not scholarly:
            missing_scholarly.append(_record_summary(record))
            continue
        by_scholarly.setdefault(str(scholarly), []).append(record)

    multiplicity = Counter(len(group) for group in by_scholarly.values())
    duplicate_groups: list[dict[str, Any]] = []
    group_class_counts: Counter[str] = Counter()
    pair_class_counts: Counter[str] = Counter()

    for scholarly_id in sorted(by_scholarly):
        group = sorted(by_scholarly[scholarly_id], key=lambda record: record["source_record_id"])
        if len(group) < 2:
            continue
        pairs: list[dict[str, str]] = []
        classifications: list[str] = []
        for left, right in combinations(group, 2):
            classification = _classify_pair(left, right)
            classifications.append(classification)
            pair_class_counts[classification] += 1
            pairs.append(
                {
                    "left": left["source_record_id"],
                    "right": right["source_record_id"],
                    "classification": classification,
                }
            )
        group_classification = max(
            classifications,
            key=lambda classification: CLASS_SEVERITY[classification],
        )
        group_class_counts[group_classification] += 1
        duplicate_groups.append(
            {
                "scholarly_id": scholarly_id,
                "copy_count": len(group),
                "classification": group_classification,
                "records": [_record_summary(record) for record in group],
                "pair_classifications": pairs,
            }
        )

    scholarly_ids = set(by_scholarly)
    witness_relations: list[dict[str, Any]] = []
    witness_by_source: dict[str, dict[str, Any]] = {}
    unresolved_witnesses: list[dict[str, str]] = []
    for record in records:
        witness = record["witness"]
        if not witness:
            continue
        witness_text = str(witness)
        witness_cts_targets = _extract_witness_cts_targets(witness_text)
        is_cts = bool(CTS_URN_RE.fullmatch(witness_text))
        witness_kind = "cts" if is_cts else "free_text"
        resolved_targets = [
            target for target in witness_cts_targets if target in scholarly_ids
        ]
        unresolved_targets = [
            target for target in witness_cts_targets if target not in scholarly_ids
        ]
        resolved: bool | None = not unresolved_targets if is_cts else None
        relation = {
            "source_record_id": record["source_record_id"],
            "source": record["source"],
            "scholarly_id": record["scholarly_id"],
            "witness": witness_text,
            "witness_kind": witness_kind,
            "witness_resolved": resolved,
            "witness_cts_targets": witness_cts_targets,
            "resolved_witness_cts_targets": resolved_targets,
            "unresolved_witness_cts_targets": unresolved_targets,
        }
        witness_relations.append(relation)
        witness_by_source[record["source_record_id"]] = relation
        for target in unresolved_targets:
            unresolved_witnesses.append(
                {
                    "source_record_id": record["source_record_id"],
                    "scholarly_id": record["scholarly_id"] or "",
                    "witness": witness_text,
                    "target": target,
                }
            )

    redundant_records: list[dict[str, Any]] = []
    redundant_without_witness = 0
    for record in records:
        if record["redundant"] != "yes":
            continue
        witness = record["witness"]
        relation = witness_by_source.get(record["source_record_id"])
        redundant_records.append(
            {
                "source_record_id": record["source_record_id"],
                "source": record["source"],
                "scholarly_id": record["scholarly_id"],
                "witness": witness,
                "witness_kind": relation["witness_kind"] if relation else None,
                "witness_resolved": relation["witness_resolved"] if relation else None,
            }
        )
        if not witness:
            redundant_without_witness += 1

    metadata_error_records = [
        {
            "source_record_id": record["source_record_id"],
            "source": record["source"],
            "error": record["metadata_error"],
        }
        for record in records
        if record["metadata_error"] is not None
    ]
    duplicate_meta_records = [
        {
            "source_record_id": record["source_record_id"],
            "source": record["source"],
            "duplicates": record["duplicate_meta_attributes"],
        }
        for record in records
        if record["duplicate_meta_attributes"]
    ]
    identity_conflict_records = [
        {
            "source_record_id": record["source_record_id"],
            "source": record["source"],
            "values": record["identity_conflict_values"],
        }
        for record in records
        if record["identity_status"] == "conflicting_document_cts_urn"
    ]
    malformed_identity_records = [
        {
            "source_record_id": record["source_record_id"],
            "source": record["source"],
            "value": record["malformed_identity_value"],
        }
        for record in records
        if record["identity_status"] == "malformed_document_cts_urn"
    ]
    documented_overlaps, unmatched_documented_overlaps, documented_class_counts = (
        _documented_collection_overlaps(records)
    )

    return {
        "document_count": len(records),
        "scholarly_identity_count": len(by_scholarly),
        "scholarly_identity_multiplicity": {
            str(count): multiplicity[count] for count in sorted(multiplicity)
        },
        "missing_scholarly_identity_records": missing_scholarly,
        "identity_conflict_records": identity_conflict_records,
        "malformed_scholarly_identity_records": malformed_identity_records,
        "duplicate_scholarly_identity_count": len(duplicate_groups),
        "duplicate_scholarly_identities": duplicate_groups,
        "group_classification_counts": {
            key: group_class_counts[key] for key in sorted(CLASS_SEVERITY)
        },
        "pair_classification_counts": {
            key: pair_class_counts[key] for key in sorted(CLASS_SEVERITY)
        },
        "documented_collection_overlap_count": len(documented_overlaps),
        "documented_collection_overlaps": documented_overlaps,
        "documented_collection_overlap_class_counts": documented_class_counts,
        "unmatched_documented_collection_overlaps": unmatched_documented_overlaps,
        "witness_relation_count": len(witness_relations),
        "witness_relations": sorted(
            witness_relations, key=lambda item: item["source_record_id"]
        ),
        "redundant_record_count": len(redundant_records),
        "redundant_records": sorted(
            redundant_records, key=lambda item: item["source_record_id"]
        ),
        "redundant_without_witness_count": redundant_without_witness,
        "unresolved_witness_relations": sorted(
            unresolved_witnesses,
            key=lambda item: (item["source_record_id"], item["witness"], item["target"]),
        ),
        "metadata_error_records": metadata_error_records,
        "duplicate_meta_attribute_records": duplicate_meta_records,
        "records": [_record_summary(record) for record in records],
    }


def render_report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "upstream",
        type=Path,
        help="Pinned CopticScriptorium/corpora checkout",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON report here instead of stdout",
    )
    args = parser.parse_args(argv)

    rendered = render_report_json(audit_upstream(args.upstream))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
