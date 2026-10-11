"""Pinned Coptic-only alignment-code pilot with independently pinned Greek TF parent.

No Greek or Coptic text appears in reports or output. This script only reads
the Greek parent and resolves address candidates in CopticScriptorium-TF.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tf.fabric import Fabric
from copticscriptorium_tf.nt_reference import (
    GREEK_NT_EDITION, resolve_coptic_sbl_references,
)
from copticscriptorium_tf.parser import parse_tt_record

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
SBL_PARENT_PIN = "4dd0207bda66133fdfa9740ff0aae7de61228700"
SOURCES = (
    ("sahidica.mark", "sahidica.mark", "Mark_02", 28, 24),
    ("sahidica.1corinthians", "sahidica.1corinthians", "1Cor_02", 16, 9),
    ("coptic-treebank", "coptic.treebank", "Mark_02", 28, 24),
)

def require_pin(path: Path, revision: str) -> None:
    actual = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if actual != revision:
        raise ValueError("wrong exact upstream repository revision")
    dirty = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if dirty:
        raise ValueError("pinned upstream source checkout has local changes")

def main(coptic_root: Path, greek_root: Path) -> None:
    require_pin(coptic_root, COPTIC_PIN)
    require_pin(greek_root, SBL_PARENT_PIN)
    tf_root = greek_root / "tf" / "2022"
    api = Fabric(locations=[str(tf_root)], silent="deep").load("book chapter verse", silent="deep")
    if not api:
        raise ValueError("pinned Greek NT parent TF could not reload")
    if (len(api.F.otype.s("verse")) != 7927 or api.F.otype.maxSlot != 137554):
        raise ValueError("wrong Greek NT parent warp profile")
    totals = Counter()
    sources = []
    for corpus, dataset, stem, expected_greek, expected_app in SOURCES:
        rel = f"{corpus}/{dataset}_TT/{stem}.tt"
        d = parse_tt_record(
            (coptic_root / rel).read_bytes(),
            source_record_id=f"{corpus}/{dataset}:{stem}", source_path=rel,
            upstream_repository="CopticScriptorium/corpora", upstream_commit=COPTIC_PIN,
        )
        sbl_counts = Counter(a.kind for a in d.sbl_annotations)
        if (sbl_counts["sbl_greek"], sbl_counts["sbl_apparatus"]) != (expected_greek, expected_app):
            raise ValueError(f"unexpected pinned SBL annotation census for {rel}")
        def lookup(book, chapter, verse):
            try:
                return api.T.nodeFromSection((book, chapter, verse))
            except (KeyError, ValueError):
                return None
        result = resolve_coptic_sbl_references(d, lookup=lookup)
        if len(result) != sum(sbl_counts.values()):
            raise ValueError("source SBL annotations disappeared from resolver")
        counts = Counter(c.status for c in result)
        for c in result:
            if c.status == "reference_candidate":
                if not c.shared_id or not c.target_node or GREEK_NT_EDITION not in c.shared_id:
                    raise ValueError("candidate missing edition-qualified target")
                if api.T.sectionFromNode(c.target_node) != (
                    c.target_book, c.target_chapter, c.target_verse
                ):
                    raise ValueError("target Greek NT node is not the claimed verse")
            elif c.target_node is not None or c.shared_id is not None:
                raise ValueError("unresolved source has an invented Greek target")
        totals.update(counts)
        sources.append({"source_path": rel, "annotations": len(result), "statuses": dict(sorted(counts.items()))})
    if totals["reference_candidate"] < 1:
        raise ValueError("no real SBL Greek NT verse candidates")
    print(json.dumps({
        "status": "pass",
        "claim": "source-backed reference candidates, not textual or word alignment",
        "coptic_source_pin": COPTIC_PIN,
        "greek_nt_parent_pin": SBL_PARENT_PIN,
        "greek_edition_ref_id": GREEK_NT_EDITION,
        "sources": sources,
        "total": sum(totals.values()),
        "statuses": dict(sorted(totals.items())),
    }, sort_keys=True))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue113_nt_reference.py COPTIC_ROOT SBLGNT_REPO")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
