"""Full pinned Coptic SBL annotation -> Greek NT verse candidate audit.

Streams all 2,628 physical TT records, including ZIP members. Parses just 48
annotated records; loads Greek Text-Fabric as an immutable read-only parent.
Report contains counts, statuses and bounded source coordinates, no corpus text.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tf.fabric import Fabric
from copticscriptorium_tf.nt_reference import resolve_coptic_sbl_references
from copticscriptorium_tf.nt_reference_audit import CandidateAudit
from copticscriptorium_tf.nt_source_diagnostics import NonCandidateInventory
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.sbl_source_census import records, expected_sbl

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
GREEK_PIN = "4dd0207bda66133fdfa9740ff0aae7de61228700"
EXPECTED_RECORDS = 2628
EXPECTED_ANNOTATED = 48
EXPECTED_KINDS = {"sbl_greek": 1652, "sbl_apparatus": 1095}


def verify_repo(root: Path, revision: str) -> None:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    if git("rev-parse", "HEAD") != revision:
        raise ValueError("wrong pinned source checkout Git commit")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("pinned source checkout has uncommitted modifications")


def audit(coptic_root: Path, greek_root: Path) -> dict:
    verify_repo(coptic_root, COPTIC_PIN)
    verify_repo(greek_root, GREEK_PIN)
    api = Fabric(locations=[str((greek_root / "tf" / "2022").resolve())], silent="deep").load(
        "book chapter verse", silent="deep",
    )
    if not api or api.F.otype.maxSlot != 137554 or len(api.F.otype.s("verse")) != 7927:
        raise ValueError("pinned Greek NT Text-Fabric warp mismatch")

    def lookup(book: str, chapter: int, verse: int):
        try:
            node = api.T.nodeFromSection((book, chapter, verse))
        except (ValueError, KeyError):
            return None
        if node is not None and api.F.otype.v(node) != "verse":
            raise ValueError("Greek NT parent section resolved to non-verse node")
        return node

    def reverse(node: int):
        if api.F.otype.v(node) != "verse":
            raise ValueError("Greek candidate is not parent verse node")
        return api.T.sectionFromNode(node)

    counter = CandidateAudit()
    anomalies = NonCandidateInventory()
    for record, source_path, raw, packaging in records(coptic_root):
        originals = expected_sbl(raw)
        if not originals:
            counter.add_unannotated(record)
            continue
        doc = parse_tt_record(
            raw, source_record_id=record, source_path=source_path, packaging=packaging,
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=COPTIC_PIN,
        )
        if [(a.kind, a.value) for a in doc.sbl_annotations] != originals:
            raise ValueError(f"TT source annotation literal/order changed: {record}")
        refs = resolve_coptic_sbl_references(doc, lookup=lookup)
        counter.add(record, originals, refs, reverse_lookup=reverse)
        anomalies.add(record, originals, refs)
    result = counter.finish(
        expected_physical=EXPECTED_RECORDS,
        expected_annotated=EXPECTED_ANNOTATED,
        expected_kinds=EXPECTED_KINDS,
    )
    result["noncandidate_source_shapes"] = anomalies.finish(
        expected_statuses={
            "reference_candidate": 2494,
            "ambiguous": 244,
            "unresolved": 8,
            "edition_unavailable": 1,
        },
        expected_annotated=EXPECTED_ANNOTATED,
        expected_total=sum(EXPECTED_KINDS.values()),
    )
    if result["noncandidate_source_shapes"]["statuses"] != result["statuses"]:
        raise ValueError("source diagnosis and Greek NT candidate audit statuses disagree")
    result["coptic_source_pin"] = COPTIC_PIN
    result["greek_parent_pin"] = GREEK_PIN
    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue113_all_source_audit.py COPTIC_ROOT GREEK_ROOT")
    print(json.dumps(audit(Path(sys.argv[1]), Path(sys.argv[2])),
                     ensure_ascii=False, sort_keys=True, indent=2))
