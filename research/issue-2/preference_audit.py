"""Evaluate explicit non-destructive preference views from issue #2 identity evidence.

This module consumes the machine-readable identity audit rather than rereading TT.
Identity classification remains authoritative in ``identity_audit.py``; this file only
measures whether proposed user-facing views have a unique evidence-based choice.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PARSING_RANK = {"automatic": 1, "checked": 2, "gold": 3}
CONVENIENCE_TREEBANK_DATASETS = {
    "coptic-treebank/coptic.treebank",
    "bohairic-treebank/bohairic.treebank",
}
CORE_EQUIVALENT_CLASSES = {"byte_identical", "core_identical_source_variant"}


def _best_parsing(group: dict[str, Any]) -> dict[str, Any]:
    records = sorted(group.get("records", []), key=lambda item: item["source_record_id"])
    scored: list[tuple[int, str]] = []
    unknown: list[str] = []
    for record in records:
        source_id = str(record["source_record_id"])
        quality = record.get("parsing_quality")
        score = PARSING_RANK.get(str(quality)) if quality is not None else None
        if score is None:
            unknown.append(source_id)
        else:
            scored.append((score, source_id))

    if not scored:
        return {
            "best_parsing_candidates": [],
            "best_parsing_quality": None,
            "best_parsing_tie": False,
            "best_parsing_status": "missing_quality",
            "unknown_quality_records": sorted(unknown),
        }

    if unknown:
        return {
            "best_parsing_candidates": [],
            "best_parsing_quality": None,
            "best_parsing_tie": False,
            "best_parsing_status": "incomplete_quality",
            "unknown_quality_records": sorted(unknown),
        }

    best_score = max(score for score, _ in scored)
    candidates = sorted(source_id for score, source_id in scored if score == best_score)
    quality = next(name for name, rank in PARSING_RANK.items() if rank == best_score)
    return {
        "best_parsing_candidates": candidates,
        "best_parsing_quality": quality,
        "best_parsing_tie": len(candidates) > 1,
        "best_parsing_status": "tie" if len(candidates) > 1 else "unique",
        "unknown_quality_records": [],
    }


def _source_preferred(group: dict[str, Any]) -> dict[str, Any]:
    records = sorted(group.get("records", []), key=lambda item: item["source_record_id"])
    if group.get("classification") not in CORE_EQUIVALENT_CLASSES:
        return {
            "source_preferred_candidate": None,
            "source_preferred_status": "ineligible_non_equivalent",
        }

    treebank = [
        record
        for record in records
        if record.get("dataset") in CONVENIENCE_TREEBANK_DATASETS
    ]
    source = [
        record
        for record in records
        if record.get("dataset") not in CONVENIENCE_TREEBANK_DATASETS
    ]
    if len(treebank) != 1 or len(source) != 1:
        return {
            "source_preferred_candidate": None,
            "source_preferred_status": "ineligible_ambiguous_topology",
        }
    return {
        "source_preferred_candidate": source[0]["source_record_id"],
        "source_preferred_status": "eligible",
    }


def evaluate_identity_report(identity_report: dict[str, Any]) -> dict[str, Any]:
    groups = identity_report.get("duplicate_scholarly_identities")
    if not isinstance(groups, list):
        raise ValueError("identity report lacks duplicate_scholarly_identities list")

    preferences: list[dict[str, Any]] = []
    best_unique = 0
    best_tie = 0
    best_missing = 0
    best_incomplete = 0
    source_eligible = 0
    source_ineligible = 0

    for group in sorted(groups, key=lambda item: str(item.get("scholarly_id", ""))):
        scholarly_id = group.get("scholarly_id")
        if not isinstance(scholarly_id, str) or not scholarly_id:
            raise ValueError("duplicate group lacks scholarly_id")
        best = _best_parsing(group)
        source = _source_preferred(group)
        if best["best_parsing_status"] == "unique":
            best_unique += 1
        elif best["best_parsing_status"] == "tie":
            best_tie += 1
        elif best["best_parsing_status"] == "missing_quality":
            best_missing += 1
        elif best["best_parsing_status"] == "incomplete_quality":
            best_incomplete += 1
        else:
            raise ValueError(
                f"unknown best parsing status {best['best_parsing_status']!r}"
            )
        if source["source_preferred_status"] == "eligible":
            source_eligible += 1
        else:
            source_ineligible += 1
        preferences.append(
            {
                "scholarly_id": scholarly_id,
                "classification": group.get("classification"),
                **best,
                **source,
            }
        )

    return {
        "source_provenance": identity_report.get("source_provenance"),
        "duplicate_group_count": len(groups),
        "best_parsing_unique_winner_group_count": best_unique,
        "best_parsing_tie_group_count": best_tie,
        "best_parsing_missing_quality_group_count": best_missing,
        "best_parsing_incomplete_quality_group_count": best_incomplete,
        "source_preferred_eligible_group_count": source_eligible,
        "source_preferred_ineligible_group_count": source_ineligible,
        "duplicate_group_preferences": preferences,
    }


def render_report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    identity_report = json.loads(args.identity_report.read_text(encoding="utf-8"))
    report = evaluate_identity_report(identity_report)
    rendered = render_report_json(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
