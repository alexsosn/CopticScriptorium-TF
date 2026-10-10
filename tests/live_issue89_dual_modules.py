"""Live three-book Coptic↔LXX native dual-TF-module acceptance.

Downloads neither source corpus nor Greek data: CI checks out exact revisions.
Neither a matching reference address nor this module establishes translated
textual/lexical alignment.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tf.fabric import Fabric

from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.lxx_modules import (
    LxxModuleError, project_reference_modules, validate_lxx_release,
)
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.writer import write_graph

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
SOURCES = (
    ("sahidic.ruth", "sahidic.ruth", "Ruth_02.tt", 23),
    ("sahidic.jonah", "sahidic.jonah", "Jonah_02.tt", 11),
    ("bohairic-habakkuk", "bohairic.habakkuk", "bohairic.Habakkuk_02.tt", 20),
)


def main(source_root: Path, greek_tf_dir: Path) -> None:
    docs = []
    for corpus, dataset, name, _expected in SOURCES:
        relative = f"{corpus}/{dataset}_TT/{name}"
        docs.append(
            parse_tt_record(
                (source_root / relative).read_bytes(),
                source_record_id=f"{corpus}/{dataset}:{name[:-3]}",
                source_path=relative,
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit=COPTIC_PIN,
            )
        )
    with TemporaryDirectory(prefix="coptic-lxx-reference-") as temporary:
        root = Path(temporary)
        coptic_parent = root / "coptic-parent"
        write_graph(build_graph(docs), coptic_parent)
        coptic_api = Fabric(locations=[str(coptic_parent)], silent="deep").load(
            "source_record_id source_word_ordinal source_sha256 norm verse_n",
            silent="deep",
        )
        assert coptic_api
        greek_api = Fabric(locations=[str(greek_tf_dir)], silent="deep").load(
            "book chapter verse subverse word orig_order",
            silent="deep",
        )
        assert greek_api

        # Negative trust tests must fail BEFORE attempting publication.
        invalid_release = root / "incorrect-lxx"
        invalid_release.mkdir()
        (invalid_release / "otype.tf").write_text("@node\n\n", encoding="utf-8")
        try:
            validate_lxx_release(invalid_release, greek_api)
        except LxxModuleError as exc:
            assert "fingerprint mismatch" in str(exc)
        else:
            raise AssertionError("wrong pinned LXX feature fingerprint was accepted")
        wrong_source = replace(docs[0], source_sha256="0" * 64)
        destination = root / "must-not-exist"
        try:
            project_reference_modules(
                (wrong_source,),
                coptic_api=coptic_api, lxx_api=greek_api,
                lxx_tf_dir=greek_tf_dir, destination=destination,
            )
        except LxxModuleError as exc:
            assert "different source bytes" in str(exc)
        else:
            raise AssertionError("Coptic parent/source SHA mismatch was accepted")
        assert not destination.exists()

        output = root / "dual-reference-modules"
        summary = project_reference_modules(
            docs,
            coptic_api=coptic_api, lxx_api=greek_api,
            lxx_tf_dir=greek_tf_dir, destination=output,
        )
        assert summary["reference_candidate"] == 54, summary
        assert summary["candidate_lxx_verse_nodes"] == 54, summary
        assert summary["ambiguous"] == 0 if "ambiguous" in summary else True
        assert summary["unresolved"] == 0 if "unresolved" in summary else True
        assert all(not list(output.rglob(name)) for name in (
            "otype.tf", "oslots.tf", "otext.tf", "*.json", "*.tsv", "*.xml"
        )), "module contains forbidden warp or semantic sidecar"
        # Reload each independently against its corresponding parent warp.
        loaded_coptic = Fabric(
            locations=[str(coptic_parent), str(output / "coptic")], silent="deep"
        ).load("coptic_lxx_ref_id coptic_lxx_ref_status source_record_id", silent="deep")
        assert loaded_coptic, "Coptic module could not be loaded with native parent warp"
        loaded_lxx = Fabric(
            locations=[str(greek_tf_dir), str(output / "lxx")], silent="deep"
        ).load("coptic_lxx_ref_id coptic_lxx_source_span_count book verse", silent="deep")
        assert loaded_lxx, "LXX module could not be loaded with native Greek parent warp"
        assert loaded_coptic.F.otype.maxSlot == sum(len(d.words) for d in docs)
        assert loaded_lxx.F.otype.maxSlot == 623693
        ids_coptic = set()
        for slot in range(1, loaded_coptic.F.otype.maxSlot + 1):
            rid = loaded_coptic.F.coptic_lxx_ref_id.v(slot)
            status = loaded_coptic.F.coptic_lxx_ref_status.v(slot)
            assert status in {"reference_candidate", "unresolved", "ambiguous", "unclassified_corpus"}
            if rid is not None:
                assert status == "reference_candidate"
                ids_coptic.add(rid)
        ids_lxx = set()
        for verse_node in loaded_lxx.F.otype.s("verse"):
            rid = loaded_lxx.F.coptic_lxx_ref_id.v(verse_node)
            if rid:
                ids_lxx.add(rid)
                assert loaded_lxx.F.coptic_lxx_source_span_count.v(verse_node) >= 1
        assert len(ids_coptic) == len(ids_lxx) == 54, (len(ids_coptic),len(ids_lxx))
        assert ids_coptic == ids_lxx, "Coptic and LXX projections do not share identical stable IDs"
        print(json.dumps({
            "status": "PASS",
            "claim": "54 matching Coptic/LXX verse addresses; not verified translation alignment",
            "input_coptic_documents": len(docs),
            "native_coptic_word_slots": loaded_coptic.F.otype.maxSlot,
            "native_greek_word_slots": loaded_lxx.F.otype.maxSlot,
            "shared_reference_ids": len(ids_coptic),
            "Greek_verse_nodes_annotated": len(ids_lxx),
            "counts": summary,
            "upstream_coptic_commit": COPTIC_PIN,
            "upstream_lxx_commit": "f32a98eddf7eb239aa73ab863d70381e416d5076",
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue89_dual_modules.py COPTIC_SOURCE_ROOT LXX_TF_ROOT")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
