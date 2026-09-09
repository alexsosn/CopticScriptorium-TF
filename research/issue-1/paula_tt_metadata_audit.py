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
    ``anno_*.xml`` document metadata.  Outer Bohairic wrapper ZIPs add another
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


def reconcile_reports(paula_report: dict[str, Any], tt_report: dict[str, Any]) -> dict[str, Any]:
    document_counts: Counter[str] = Counter()
    corpus_counts: Counter[str] = Counter()
    document_records: set[tuple[str, str]] = set()
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
            document_records.add((str(instance["dataset"]), record.casefold()))
        else:
            corpus_counts[feature_type] += 1

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
        "paula_document_record_count": len(document_records),
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
