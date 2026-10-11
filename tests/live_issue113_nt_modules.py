"""Real pinned Coptic-owned NT bilateral weft-only Text-Fabric round-trip.

Build a SMALL 3-document native Coptic warp locally, load untouched pinned
Greek NT TF, project source-attested verse candidates, then reload both with
additive sparse features. No generated corpora or copyrighted strings uploaded.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tf.fabric import Fabric
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.nt_modules import (
    GREEK_PARENT_PIN, project_nt_modules, validate_native_module_parent,
)
from copticscriptorium_tf.nt_reference import COPTIC_PIN
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.writer import write_graph

SOURCES = (
    ("sahidica.mark", "sahidica.mark", "Mark_02"),
    ("sahidica.1corinthians", "sahidica.1corinthians", "1Cor_02"),
    ("coptic-treebank", "coptic.treebank", "Mark_02"),
)


def check_git(root: Path, revision: str):
    def call(*args):
        return subprocess.run(["git", "-C", str(root), *args],
                              text=True, capture_output=True, check=True).stdout.strip()
    if call("rev-parse", "HEAD") != revision or call("status", "--porcelain"):
        raise ValueError("modified or incorrectly pinned parent source revision")


def main(coptic_root: Path, greek_root: Path) -> dict:
    check_git(coptic_root, COPTIC_PIN)
    check_git(greek_root, GREEK_PARENT_PIN)
    docs = []
    for corpus, dataset, name in SOURCES:
        rel = f"{corpus}/{dataset}_TT/{name}.tt"
        docs.append(parse_tt_record(
            (coptic_root / rel).read_bytes(), source_record_id=f"{corpus}/{dataset}:{name}",
            source_path=rel, upstream_repository="CopticScriptorium/corpora",
            upstream_commit=COPTIC_PIN,
        ))
    graph = build_graph(docs)
    if validate_graph(graph):
        raise ValueError("Coptic native TF graph failed structural validation")
    greek_dir = greek_root / "tf" / "2022"
    greek_api = Fabric(locations=[str(greek_dir.resolve())], silent="deep").load(
        "book chapter verse", silent="deep",
    )
    if not greek_api:
        raise ValueError("pinned Greek NT parent failed to load")
    with TemporaryDirectory(prefix="coptic-nt-weft-pilot-") as tmp:
        root = Path(tmp)
        coptic_dir = root / "coptic"
        wefts = root / "wefts"
        write_graph(graph, coptic_dir)
        coptic_api = Fabric(locations=[str(coptic_dir)], silent="deep").load(
            "source_record_id source_ordinal value sbl_verse_n "
            "source_sha256 source_word_ordinal norm render_mode", silent="deep",
        )
        if not coptic_api:
            raise ValueError("real Coptic pilot TF reload failed")
        result = project_nt_modules(
            docs, coptic_api=coptic_api, greek_api=greek_api,
            coptic_tf_dir=coptic_dir, greek_tf_dir=greek_dir,
            destination=wefts,
        )
        if result["reference_candidate"] != 129 or result["coptic_annotated_sbl_nodes"] != 129:
            raise ValueError("unexpected real Mark2/1Cor2/treebank source NT candidate inventory")

        for parent in ("coptic", "greek"):
            validate_native_module_parent(
                wefts / parent, projection=parent,
                coptic_tf_dir=coptic_dir, greek_tf_dir=greek_dir,
            )
        cw = Fabric(
            locations=[str(coptic_dir), str(wefts / "coptic")], silent="deep",
        ).load("coptic_nt_ref_id coptic_nt_ref_status", silent="deep")
        gw = Fabric(
            locations=[str(greek_dir), str(wefts / "greek")], silent="deep",
        ).load("coptic_nt_ref_id coptic_nt_source_occurrence_count", silent="deep")
        if not cw or not gw:
            raise ValueError("additive native NT weft reload failed")
        coptic_nodes = tuple(cw.F.otype.s("sbl_greek")) + tuple(cw.F.otype.s("sbl_apparatus"))
        coptic_refs = Counter(cw.F.coptic_nt_ref_id.v(n) for n in coptic_nodes)
        greek_nodes = tuple(n for n in gw.F.otype.s("verse")
                            if gw.F.coptic_nt_ref_id.v(n) is not None)
        greek_refs = Counter({
            gw.F.coptic_nt_ref_id.v(n): gw.F.coptic_nt_source_occurrence_count.v(n)
            for n in greek_nodes
        })
        if (len(coptic_nodes) != 129 or sum(coptic_refs.values()) != 129
                or coptic_refs != greek_refs):
            raise ValueError("bilateral Coptic/Greek native NT reference count mismatch")
        if any(cw.F.coptic_nt_ref_id.v(n) is not None for n in range(1, cw.F.otype.maxSlot + 1)):
            raise ValueError("verse address incorrectly projected onto Coptic word slot")
        if any(gw.F.otype.v(n) != "verse" for n in greek_nodes):
            raise ValueError("Greek parent weft incorrectly projected onto nonverse")
        result["greek_verse_ref_occurrence_sum"] = sum(greek_refs.values())
        result["greek_verse_ref_nodes_reloaded"] = len(greek_nodes)
        result["coptic_sbl_ref_nodes_reloaded"] = len(coptic_nodes)
        result["status"] = "pass"
        result["scope"] = "3 pinned physical TT records only; Coptic-owned wefts, no text/word equivalence"
        return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue113_nt_modules.py COPTIC_SOURCE GREEK_PARENT")
    print(json.dumps(main(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))
