"""Run the public converter on a complete source tree and reload the result.

This is an operational converter/resource regression, not a scholarly corpus
certification. It intentionally does not compare against historical corpus
counts or classifications.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from time import monotonic

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from copticscriptorium_tf.converter import convert_source_tree

UPSTREAM_REPOSITORY = "CopticScriptorium/corpora"
UPSTREAM_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
REQUIRED_EDGE_FEATURES = (
    "dependency_head",
    "entity_head",
    "parent",
    "direct_word",
    "same_scholarly",
    "documented_overlap",
    "witness",
)
REQUIRED_EVIDENCE_EDGE_FEATURES = (
    "same_scholarly_classification",
    "documented_overlap_classification",
    "documented_overlap_family",
    "witness_literal",
    "witness_target_scholarly_id",
)
REQUIRED_FORMATS = ("text-orig-full", "text-diplomatic-full")


def _reload_and_check(tf_dir: Path, result) -> dict[str, object]:
    from tf.fabric import Fabric
    from tf.core.timestamp import DEEP

    feature_names = sorted(path.stem for path in tf_dir.glob("*.tf"))
    forbidden = [name for name in feature_names if name.endswith("_json")]
    if forbidden:
        raise RuntimeError(f"structural JSON features found: {forbidden}")

    required_edges = (*REQUIRED_EDGE_FEATURES, *REQUIRED_EVIDENCE_EDGE_FEATURES)
    requested = ["source_record_id", "norm", *required_edges]
    started = monotonic()
    api = Fabric(locations=str(tf_dir), silent=DEEP).load(" ".join(requested), silent=DEEP)
    reload_seconds = monotonic() - started
    if api is None:
        raise RuntimeError("fresh Text-Fabric reload failed")

    max_slot = api.F.otype.maxSlot
    max_node = api.F.otype.maxNode
    documents = tuple(api.F.otype.s("document"))
    if max_slot != result.slots:
        raise RuntimeError(f"slot mismatch: converter={result.slots}, reload={max_slot}")
    if max_node - max_slot != result.nodes:
        raise RuntimeError(
            f"node mismatch: converter={result.nodes}, reload={max_node - max_slot}"
        )
    if len(documents) != result.source_records:
        raise RuntimeError(
            f"document mismatch: converter={result.source_records}, reload={len(documents)}"
        )
    if not documents:
        raise RuntimeError("converter produced no document nodes")

    first_document = documents[0]
    first_section = api.T.sectionFromNode(first_document)
    if not first_section or not first_section[0]:
        raise RuntimeError("document section lookup failed after reload")

    available_formats = tuple(sorted(api.T.formats))
    for fmt in REQUIRED_FORMATS:
        if fmt not in available_formats:
            raise RuntimeError(f"required text format unavailable after reload: {fmt}")
        # Exercising both formats on a real document is the invariant; the two
        # strings need not differ for every individual source document.
        api.T.text(first_document, fmt=fmt)

    for feature in required_edges:
        if feature not in feature_names:
            raise RuntimeError(f"required native edge feature not serialized: {feature}")

    return {
        "reload_seconds": round(reload_seconds, 3),
        "reload_slots": max_slot,
        "reload_nodes": max_node - max_slot,
        "reload_documents": len(documents),
        "first_document_section": list(first_section),
        "available_formats": list(available_formats),
        "required_edge_features": list(REQUIRED_EDGE_FEATURES),
        "required_evidence_edge_features": list(REQUIRED_EVIDENCE_EDGE_FEATURES),
        "structural_json_features": forbidden,
    }


def run(source_root: Path, work_root: Path) -> dict[str, object]:
    tf_dir = work_root / "tf"
    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True)

    result = convert_source_tree(
        source_root,
        tf_dir,
        upstream_repository=UPSTREAM_REPOSITORY,
        upstream_commit=UPSTREAM_COMMIT,
    )
    reload_report = _reload_and_check(tf_dir, result)

    report = result.to_dict()
    report.update(reload_report)
    report["upstream_repository"] = UPSTREAM_REPOSITORY
    report["upstream_commit"] = UPSTREAM_COMMIT
    report["purpose"] = "converter/resource regression; not corpus certification"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        report = run(args.source_root, args.work_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as error:
        print(f"full converter smoke failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
