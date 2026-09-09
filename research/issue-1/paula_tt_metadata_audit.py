"""Reconcile PAULA metadata scope and field coverage against the TT census."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
from typing import Any


def classify_metadata_instance(instance: dict[str, Any]) -> tuple[str, str | None]:
    """Return ``(scope, record)`` for one PAULA metadata feature instance.

    Coptic Scriptorium PAULA archives use a dataset root followed either by an
    ``anno_*.xml`` corpus metadata member or a document directory containing
    ``anno_*.xml`` document metadata. Outer Bohairic wrapper ZIPs add another
    ``!/`` prefix, so only the innermost archive member path is structural.
    """

    dataset = str(instance.get("dataset") or "")
    source = str(instance.get("source") or "")
    if "/" not in dataset:
        raise ValueError(f"invalid PAULA dataset identity: {dataset!r}")
    dataset_name = dataset.split("/", 1)[1]

    member = source.split("!/")[-1]
    parts = PurePosixPath(member).parts
    if len(parts) < 2 or parts[0].casefold() != dataset_name.casefold():
        raise ValueError(
            f"PAULA metadata member {member!r} does not belong to dataset {dataset_name!r}"
        )
    if len(parts) == 2:
        return "corpus", None
    if len(parts) == 3:
        return "document", parts[1]
    raise ValueError(f"unsupported PAULA metadata member layout: {member!r}")


def classify_tt_document(document: dict[str, Any]) -> tuple[str, str]:
    """Return literal ``(dataset, record)`` identity from one TT census entry."""

    source = str(document.get("source") or "")
    if not source:
        raise ValueError("TT document has no source identity")

    if "!/" in source:
        archive_source, member = source.split("!/", 1)
        archive_parts = PurePosixPath(archive_source).parts
        if len(archive_parts) != 2:
            raise ValueError(f"unsupported TT archive source layout: {source!r}")
        corpus, archive_name = archive_parts
        suffix = "_TT.zip"
        if not archive_name.endswith(suffix) or len(archive_name) <= len(suffix):
            raise ValueError(f"unsupported TT archive source layout: {source!r}")
        dataset_name = archive_name[: -len(suffix)]
        member_parts = list(PurePosixPath(member).parts)
        if member_parts and member_parts[0].casefold() == f"{dataset_name}_TT".casefold():
            member_parts = member_parts[1:]
        if not member_parts:
            raise ValueError(f"TT archive source has no record path: {source!r}")
        record_path = PurePosixPath(*member_parts)
    else:
        parts = PurePosixPath(source).parts
        if len(parts) < 3:
            raise ValueError(f"unsupported TT directory source layout: {source!r}")
        corpus, directory_name, *record_parts = parts
        suffix = "_TT"
        if not directory_name.endswith(suffix) or len(directory_name) <= len(suffix):
            raise ValueError(f"unsupported TT directory source layout: {source!r}")
        dataset_name = directory_name[: -len(suffix)]
        record_path = PurePosixPath(*record_parts)

    if record_path.suffix.casefold() != ".tt":
        raise ValueError(f"TT source record is not a .tt file: {source!r}")
    record = record_path.as_posix()[: -len(record_path.suffix)]
    if not record:
        raise ValueError(f"TT source has empty record identity: {source!r}")
    return f"{corpus}/{dataset_name}", record


def _technical_identity(dataset: str, record: str) -> tuple[str, str]:
    return dataset.casefold(), record.casefold()


def _literal_identity(dataset: str, record: str) -> str:
    return f"{dataset}:{record}"


def _record_literal(
    index: dict[tuple[str, str], tuple[str, str]],
    dataset: str,
    record: str,
    *,
    representation: str,
) -> None:
    key = _technical_identity(dataset, record)
    literal = (dataset, record)
    previous = index.get(key)
    if previous is not None and previous != literal:
        raise ValueError(
            f"case-insensitive {representation} document collision: "
            f"{_literal_identity(*previous)!r} versus {_literal_identity(*literal)!r}"
        )
    index[key] = literal


def reconcile_reports(paula_report: dict[str, Any], tt_report: dict[str, Any]) -> dict[str, Any]:
    document_counts: Counter[str] = Counter()
    corpus_counts: Counter[str] = Counter()
    paula_records: dict[tuple[str, str], tuple[str, str]] = {}
    tt_records: dict[tuple[str, str], tuple[str, str]] = {}
    errors: list[dict[str, str]] = []

    for instance in paula_report.get("metadata_feature_instances", []):
        try:
            scope, record = classify_metadata_instance(instance)
        except ValueError as exc:
            errors.append(
                {
                    "kind": "unclassified_paula_metadata_scope",
                    "source": str(instance.get("source") or ""),
                    "type": str(instance.get("type") or ""),
                    "detail": str(exc),
                }
            )
            continue

        feature_type = str(instance.get("type") or "")
        if not feature_type:
            errors.append(
                {
                    "kind": "missing_paula_metadata_type",
                    "source": str(instance.get("source") or ""),
                    "type": "",
                    "detail": "metadata feature instance has no type",
                }
            )
            continue

        if scope == "document":
            document_counts[feature_type] += 1
            assert record is not None
            dataset = str(instance["dataset"])
            try:
                _record_literal(
                    paula_records,
                    dataset,
                    record,
                    representation="PAULA",
                )
            except ValueError as exc:
                errors.append(
                    {
                        "kind": "paula_document_identity_collision",
                        "source": str(instance.get("source") or ""),
                        "type": feature_type,
                        "detail": str(exc),
                    }
                )
        else:
            corpus_counts[feature_type] += 1

    for document in tt_report.get("documents", []):
        try:
            dataset, record = classify_tt_document(document)
            _record_literal(tt_records, dataset, record, representation="TT")
        except ValueError as exc:
            errors.append(
                {
                    "kind": "unclassified_tt_document_identity",
                    "source": str(document.get("source") or ""),
                    "type": "",
                    "detail": str(exc),
                }
            )

    paula_keys = set(paula_records)
    tt_keys = set(tt_records)
    matched_keys = paula_keys & tt_keys
    paula_only_keys = paula_keys - tt_keys
    tt_only_keys = tt_keys - paula_keys
    case_variants = [
        {
            "paula": _literal_identity(*paula_records[key]),
            "tt": _literal_identity(*tt_records[key]),
        }
        for key in sorted(matched_keys)
        if paula_records[key] != tt_records[key]
    ]

    tt_counts = {
        str(key): int(value)
        for key, value in (tt_report.get("metadata_key_presence") or {}).items()
    }
    document_fields = set(document_counts)
    tt_fields = set(tt_counts)

    count_differences: dict[str, dict[str, int]] = {}
    for field in sorted(document_fields | tt_fields):
        paula_count = document_counts[field]
        tt_count = tt_counts.get(field, 0)
        if paula_count != tt_count:
            count_differences[field] = {
                "paula": paula_count,
                "tt": tt_count,
                "delta": paula_count - tt_count,
            }

    return {
        "paula_document_record_count": len(paula_records),
        "tt_document_record_count": len(tt_records),
        "matched_document_record_count": len(matched_keys),
        "paula_only_document_records": [
            _literal_identity(*paula_records[key]) for key in sorted(paula_only_keys)
        ],
        "tt_only_document_records": [
            _literal_identity(*tt_records[key]) for key in sorted(tt_only_keys)
        ],
        "case_variant_document_pairs": case_variants,
        "document_field_counts": {key: document_counts[key] for key in sorted(document_counts)},
        "corpus_field_counts": {key: corpus_counts[key] for key in sorted(corpus_counts)},
        "document_fields_only_in_paula": sorted(document_fields - tt_fields),
        "document_fields_only_in_tt": sorted(tt_fields - document_fields),
        "document_field_count_differences": count_differences,
        "errors": sorted(
            errors,
            key=lambda item: (
                item.get("source", ""),
                item.get("kind", ""),
                item.get("type", ""),
            ),
        ),
    }


def render_report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paula-report", type=Path, required=True)
    parser.add_argument("--tt-report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    paula_report = json.loads(args.paula_report.read_text(encoding="utf-8"))
    tt_report = json.loads(args.tt_report.read_text(encoding="utf-8"))
    rendered = render_report_json(reconcile_reports(paula_report, tt_report))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
