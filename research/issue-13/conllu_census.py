"""Pinned corpus census for production CoNLL-U supplementation in issue #13."""

from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from copticscriptorium_tf.conllu import SupplementUnavailable, parse_conllu_supplement
from copticscriptorium_tf.parser import parse_source_tree


UPSTREAM_REPOSITORY = "CopticScriptorium/corpora"
UPSTREAM_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
EXPECTED = {
    "tt_document_count": 2628,
    "conllu_document_count": 2628,
    "paired_document_count": 2628,
    "valid_supplement_count": 2361,
    "valid_supplement_word_count": 2104966,
}
EXPECTED_UNAVAILABLE_REASONS = {
    "malformed_conllu": 40,
    "placeholder": 227,
}


def _load_conllu_sources_module():
    path = REPOSITORY_ROOT / "research" / "issue-1" / "conllu_sources.py"
    spec = importlib.util.spec_from_file_location("issue1_conllu_sources_for_issue13", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load reviewed CoNLL-U source iterator from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _index_unique(items: list[tuple[str, Any]], *, representation: str) -> dict[str, tuple[str, Any]]:
    result: dict[str, tuple[str, Any]] = {}
    for literal, value in items:
        key = literal.casefold()
        if key in result:
            previous = result[key][0]
            raise ValueError(
                f"case-insensitive {representation} identity collision: "
                f"{previous!r} versus {literal!r}"
            )
        result[key] = (literal, value)
    return result


def build_report(root: Path | str) -> dict[str, object]:
    root_path = Path(root)
    documents = parse_source_tree(
        root_path,
        upstream_repository=UPSTREAM_REPOSITORY,
        upstream_commit=UPSTREAM_COMMIT,
    )
    tt_index = _index_unique(
        [(document.source_record_id, document) for document in documents],
        representation="TT",
    )

    sources = _load_conllu_sources_module()
    conllu_records = list(sources.iter_conllu_records(root_path))
    conllu_index = _index_unique(
        [
            (f"{record['dataset']}:{record['record']}", record)
            for record in conllu_records
        ],
        representation="CoNLL-U",
    )

    tt_keys = set(tt_index)
    conllu_keys = set(conllu_index)
    paired_keys = sorted(tt_keys & conllu_keys)
    tt_only = [tt_index[key][0] for key in sorted(tt_keys - conllu_keys)]
    conllu_only = [conllu_index[key][0] for key in sorted(conllu_keys - tt_keys)]

    unavailable: Counter[str] = Counter()
    unavailable_records: list[dict[str, str]] = []
    unexpected_failures: list[dict[str, str]] = []
    valid_supplement_count = 0
    valid_supplement_word_count = 0

    for key in paired_keys:
        source_record_id, document = tt_index[key]
        conllu_record_id, conllu_record = conllu_index[key]
        try:
            supplement = parse_conllu_supplement(
                document,
                conllu_record["text"].encode("utf-8"),
                source_path=conllu_record["source"],
            )
        except SupplementUnavailable as exc:
            unavailable[exc.reason] += 1
            unavailable_records.append(
                {
                    "source_record_id": source_record_id,
                    "conllu_record_id": conllu_record_id,
                    "source_path": exc.source_path,
                    "reason": exc.reason,
                    "detail": exc.detail,
                }
            )
            continue
        except Exception as exc:  # pragma: no cover - fail ledger for corpus reruns
            unexpected_failures.append(
                {
                    "source_record_id": source_record_id,
                    "conllu_record_id": conllu_record_id,
                    "source_path": conllu_record["source"],
                    "exception": type(exc).__name__,
                    "detail": str(exc),
                }
            )
            continue

        valid_supplement_count += 1
        valid_supplement_word_count += len(supplement.words)

    return {
        "upstream_repository": UPSTREAM_REPOSITORY,
        "upstream_commit": UPSTREAM_COMMIT,
        "tt_document_count": len(documents),
        "conllu_document_count": len(conllu_records),
        "paired_document_count": len(paired_keys),
        "valid_supplement_count": valid_supplement_count,
        "valid_supplement_word_count": valid_supplement_word_count,
        "unavailable_reasons": {key: unavailable[key] for key in sorted(unavailable)},
        "unavailable_records": sorted(
            unavailable_records,
            key=lambda item: (
                item["reason"],
                item["source_record_id"].casefold(),
                item["source_record_id"],
            ),
        ),
        "tt_only": tt_only,
        "conllu_only": conllu_only,
        "unexpected_failures": sorted(
            unexpected_failures,
            key=lambda item: (
                item["source_record_id"].casefold(),
                item["source_record_id"],
            ),
        ),
    }


def validate_report(report: dict[str, object]) -> list[str]:
    failures: list[str] = []
    for key, expected in EXPECTED.items():
        measured = report[key]
        if measured != expected:
            failures.append(f"{key}: expected {expected}, measured {measured}")
    if report["unavailable_reasons"] != EXPECTED_UNAVAILABLE_REASONS:
        failures.append(
            "unavailable_reasons: expected "
            f"{EXPECTED_UNAVAILABLE_REASONS}, measured {report['unavailable_reasons']}"
        )
    for key in ("tt_only", "conllu_only", "unexpected_failures"):
        if report[key]:
            failures.append(f"{key}: {report[key]}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(args.upstream)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.validate:
        failures = validate_report(report)
        if failures:
            print("\n".join(failures))
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
