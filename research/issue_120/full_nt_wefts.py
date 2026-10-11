"""Complete native Coptic SBL→Greek NT bilateral weft acceptance.

Run in two separate processes after the existing full Coptic converter,
so its peak allocations are never retained when wefts are generated or
independently reloaded. Only a source-free JSON report is persisted.
"""
from __future__ import annotations

from collections import Counter
import argparse
import gc
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.nt_modules import (
    GREEK_PARENT_PIN, project_nt_modules, validate_native_module_parent,
)
from copticscriptorium_tf.nt_reference import COPTIC_PIN
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.sbl_source_census import records, expected_sbl

EXPECTED_COUNTS = {
    "reference_candidate": 2362,
    "ambiguous": 376,
    "unresolved": 8,
    "edition_unavailable": 1,
    "coptic_annotated_sbl_nodes": 2747,
    "coptic_candidate_sbl_nodes": 2362,
    "greek_target_verse_nodes": 944,
}
EXPECTED_KIND_COUNTS = {"sbl_greek": 1652, "sbl_apparatus": 1095}


def validate_full_counts(report: dict, *, physical: int, annotated: int) -> dict:
    """Reject any loss/drift, not just under-coverage or missing Greek nodes."""
    if (physical != 2628 or annotated != 48
            or report != EXPECTED_COUNTS):
        raise ValueError("complete NT source/weft count drift")
    return report


def verify_native_feature_parity(
    coptic: dict[int, tuple[str, str, str | None]],
    greek: dict[int, tuple[str, str, int]],
    *, word_max: int, greek_max_slot: int,
) -> dict:
    """Compare independent native feature maps without depending on TF tools.

    Coptic annotation nodes and Greek verse nodes have wholly separate warps.
    Numeric node IDs are never compared between corpora.
    """
    accepted = {"reference_candidate", "ambiguous", "unresolved",
                "edition_unavailable", "unclassified_source"}
    left: Counter[str] = Counter()
    states: Counter[str] = Counter()
    for node, (otype, status, ref) in coptic.items():
        if (not isinstance(node, int) or isinstance(node, bool)
                or node <= word_max or otype not in {"sbl_greek", "sbl_apparatus"}):
            raise ValueError("Coptic reference written on non-SBL node or word slot")
        if status not in accepted:
            raise ValueError("unknown Coptic candidate status")
        if (status == "reference_candidate") != (ref is not None):
            raise ValueError("Coptic candidate reference/status mismatch")
        if ref is not None:
            if not isinstance(ref, str) or not ref or "\t" in ref or "\n" in ref:
                raise ValueError("invalid Coptic reference feature")
            left[ref] += 1
        states[status] += 1
    right: Counter[str] = Counter()
    for node, (otype, ref, occurrence_count) in greek.items():
        if (not isinstance(node, int) or isinstance(node, bool)
                or node <= greek_max_slot or otype != "verse"):
            raise ValueError("Greek address attached to nonverse or word slot")
        if not isinstance(ref, str) or not ref:
            raise ValueError("missing Greek verse reference")
        if (not isinstance(occurrence_count, int) or isinstance(occurrence_count, bool)
                or occurrence_count < 1):
            raise ValueError("Greek source occurrence count invalid")
        if ref in right:
            raise ValueError("Greek reference repeated on multiple verse nodes")
        right[ref] = occurrence_count
    if left != right:
        raise ValueError("bilateral Greek/Coptic reference count mismatch")
    return {
        **dict(states),
        "coptic_annotated_sbl_nodes": len(coptic),
        "coptic_candidate_sbl_nodes": sum(left.values()),
        "distinct_greek_verses": len(greek),
        "total_greek_occurrences": sum(right.values()),
    }


def verify_git(root: Path, expected: str) -> None:
    def git(*cmd):
        return subprocess.run(
            ["git", "-C", str(root), *cmd], capture_output=True,
            text=True, check=True,
        ).stdout.strip()
    if git("rev-parse", "HEAD") != expected:
        raise ValueError("wrong parent/source Git revision")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("dirty pinned corpus repository")


def collect_annotated_documents(root: Path):
    """Stream every directory/ZIP source record, parse only original SBL records."""
    docs = []
    physical = 0
    kinds: Counter[str] = Counter()
    seen: set[str] = set()
    for identity, source_path, raw, packaging in records(root):
        if identity.casefold() in seen:
            raise ValueError("duplicate physical source document ID")
        seen.add(identity.casefold())
        physical += 1
        original = expected_sbl(raw)
        if not original:
            continue
        doc = parse_tt_record(
            raw, source_record_id=identity, source_path=source_path,
            packaging=packaging, upstream_repository="CopticScriptorium/corpora",
            upstream_commit=COPTIC_PIN,
        )
        if [(a.kind, a.value) for a in doc.sbl_annotations] != original:
            raise ValueError("source SBL attribute kind/value/ordinal drift")
        kinds.update(k for k, _literal in original)
        docs.append(doc)
    if physical != 2628 or len(docs) != 48 or dict(kinds) != EXPECTED_KIND_COUNTS:
        raise ValueError("complete pinned physical source SBL count mismatch")
    return docs, physical


def project(source_root: Path, greek_root: Path, coptic_tf: Path, destination: Path) -> dict:
    from tf.fabric import Fabric

    verify_git(source_root, COPTIC_PIN)
    verify_git(greek_root, GREEK_PARENT_PIN)
    docs, physical = collect_annotated_documents(source_root)
    greek_tf = greek_root / "tf" / "2022"
    greek = Fabric(locations=[str(greek_tf)], silent="deep").load(
        "book chapter verse", silent="deep")
    if not greek:
        raise ValueError("Greek NT parent failed to reload")
    coptic = Fabric(locations=[str(coptic_tf)], silent="deep").load(
        "source_record_id source_ordinal value sbl_verse_n "
        "source_sha256 source_word_ordinal norm render_mode", silent="deep")
    if not coptic:
        raise ValueError("full Coptic TF parent failed to reload")
    if (coptic.F.otype.maxSlot != 2394354
            or len(coptic.F.otype.s("document")) != 2628):
        raise ValueError("full Coptic parent warp source/document count mismatch")
    counts = project_nt_modules(
        docs, coptic_api=coptic, greek_api=greek,
        coptic_tf_dir=coptic_tf, greek_tf_dir=greek_tf,
        destination=destination,
    )
    validate_full_counts(counts, physical=physical, annotated=len(docs))
    for projection in ("coptic", "greek"):
        validate_native_module_parent(
            destination / projection, projection=projection,
            coptic_tf_dir=coptic_tf, greek_tf_dir=greek_tf)
    return {
        "status": "pass",
        "stage": "full-project",
        "coptic_source_pin": COPTIC_PIN,
        "greek_parent_pin": GREEK_PARENT_PIN,
        "coptic_words": 2394354,
        "physical_records": physical,
        "annotated_physical_records": len(docs),
        "source_sbl_kinds": dict(sorted(EXPECTED_KIND_COUNTS.items())),
        "module_tf_file_counts": {
            projection: len(list((destination / projection).glob("*.tf")))
            for projection in ("coptic", "greek")
        },
        "module_bytes": sum(path.stat().st_size for path in destination.rglob("*.tf")),
        "counts": counts,
    }


def verify(source_root: Path, greek_root: Path, coptic_tf: Path, destination: Path) -> dict:
    """Fresh TF reader; checks actual module node data, not project() return."""
    from tf.fabric import Fabric

    verify_git(source_root, COPTIC_PIN)
    verify_git(greek_root, GREEK_PARENT_PIN)
    greek_tf = greek_root / "tf" / "2022"
    for projection in ("coptic", "greek"):
        validate_native_module_parent(
            destination / projection, projection=projection,
            coptic_tf_dir=coptic_tf, greek_tf_dir=greek_tf)
    ca = Fabric(locations=[str(coptic_tf), str(destination/"coptic")],
                silent="deep").load(
        "coptic_nt_ref_id coptic_nt_ref_status", silent="deep")
    if not ca or ca.F.otype.maxSlot != 2394354:
        raise ValueError("invalid complete Coptic plus native NT module load")
    statuses = dict(ca.F.coptic_nt_ref_status.items())
    refs = dict(ca.F.coptic_nt_ref_id.items())
    if set(refs) - set(statuses):
        raise ValueError("Coptic candidate without source SBL status")
    coptic = {
        node: (ca.F.otype.v(node), status, refs.get(node))
        for node, status in statuses.items()
    }
    if (len(ca.F.otype.s("sbl_greek")) != 1652
            or len(ca.F.otype.s("sbl_apparatus")) != 1095):
        raise ValueError("native Coptic SBL node population changed")
    del ca, statuses, refs
    gc.collect()

    ga = Fabric(locations=[str(greek_tf), str(destination/"greek")],
                silent="deep").load(
        "coptic_nt_ref_id coptic_nt_source_occurrence_count", silent="deep")
    if not ga or ga.F.otype.maxSlot != 137554 or len(ga.F.otype.s("verse")) != 7927:
        raise ValueError("invalid pinned Greek native NT module load")
    greek_refs = dict(ga.F.coptic_nt_ref_id.items())
    greek_counts = dict(ga.F.coptic_nt_source_occurrence_count.items())
    if set(greek_refs) != set(greek_counts):
        raise ValueError("Greek reference and count feature node keys differ")
    greek = {
        node: (ga.F.otype.v(node), ref, greek_counts[node])
        for node, ref in greek_refs.items()
    }
    counts = verify_native_feature_parity(coptic, greek,
        word_max=2394354, greek_max_slot=137554)
    if (counts["coptic_annotated_sbl_nodes"] != 2747
        or counts["coptic_candidate_sbl_nodes"] != 2362
        or counts["distinct_greek_verses"] != 944
        or counts["total_greek_occurrences"] != 2362
        or counts.get("ambiguous") != 376
        or counts.get("unresolved") != 8
        or counts.get("edition_unavailable") != 1
        or counts.get("reference_candidate") != 2362
        or set(counts) != {
            "coptic_annotated_sbl_nodes", "coptic_candidate_sbl_nodes",
            "distinct_greek_verses", "total_greek_occurrences",
            "reference_candidate", "ambiguous", "unresolved",
            "edition_unavailable",
        }):
        raise ValueError("full native TF reload/reference count drift")
    return {
        "status": "pass", "stage": "independent-native-reload",
        "scope": "Coptic-owned source-grounded verse-address candidates; NOT Greek word alignment",
        "coptic_words": 2394354,
        "greek_words": 137554,
        "greek_verses": 7927,
        "counts": counts,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("project", "verify"))
    parser.add_argument("source_root", type=Path)
    parser.add_argument("greek_root", type=Path)
    parser.add_argument("--coptic-tf", type=Path, required=True)
    parser.add_argument("--wefts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    operation = project if args.mode == "project" else verify
    report = operation(args.source_root, args.greek_root, args.coptic_tf, args.wefts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
