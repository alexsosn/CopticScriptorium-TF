"""Live source-locked Coptic OT ↔ Greek LXX inverse-witness query acceptance.

Fetches neither corpus itself: CI checks out exact source commits. No words or
derived corpus are uploaded. The result describes shared reference addresses,
not Coptic↔Greek textual or lexical equivalence.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tf.fabric import Fabric
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.writer import write_graph
from copticscriptorium_tf.lxx_module import (
    COPTIC_PIN, LXX_PIN, materialize_lxx_reference_modules,
    verify_coptic_module_parent,
)
from copticscriptorium_tf.lxx_modules import validate_lxx_release
from copticscriptorium_tf.lxx_query import find_coptic_witnesses

SOURCES = (
    ("sahidic.ruth", "sahidic.ruth", "Ruth_02.tt"),
    ("sahidic.jonah", "sahidic.jonah", "Jonah_02.tt"),
    ("bohairic-jonah", "bohairic.jonah", "bohairic.Jonah_02.tt"),
    ("bohairic-habakkuk", "bohairic.habakkuk", "bohairic.Habakkuk_02.tt"),
)


def main(coptic_source: Path, greek_parent: Path) -> None:
    docs = []
    for corpus, dataset, name in SOURCES:
        rel = f"{corpus}/{dataset}_TT/{name}"
        docs.append(parse_tt_record(
            (coptic_source / rel).read_bytes(),
            source_record_id=f"{corpus}/{dataset}:{name[:-3]}",
            source_path=rel,
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=COPTIC_PIN,
        ))

    with TemporaryDirectory(prefix="coptic-lxx-inverse-") as temp:
        root = Path(temp)
        coptic_parent = root / "coptic-parent"
        write_graph(build_graph(docs), coptic_parent)

        source_api = Fabric(locations=[str(coptic_parent)], silent="deep").load(
            "source_record_id source_word_ordinal source_sha256", silent="deep"
        )
        greek_api = Fabric(locations=[str(greek_parent)], silent="deep").load(
            "book chapter verse subverse", silent="deep"
        )
        assert source_api and greek_api
        validate_lxx_release(greek_parent, greek_api)

        modules = root / "modules"
        produced = materialize_lxx_reference_modules(
            documents=docs,
            coptic_api=source_api,
            lxx_api=greek_api,
            output_root=modules,
            lxx_parent_commit=LXX_PIN,
            coptic_source_commit=COPTIC_PIN,
            coptic_parent_tf=coptic_parent,
            lxx_parent_tf=greek_parent,
        )
        assert produced.source_documents == 4
        assert produced.lxx_candidate_verses == 54
        verify_coptic_module_parent(modules / "coptic", coptic_parent)
        # This is the current *source-locked* module: no older count feature.
        assert not (modules / "lxx" / "coptic_lxx_source_span_count.tf").exists()

        coptic = Fabric(
            locations=[str(coptic_parent), str(modules / "coptic")],
            silent="deep",
        ).load(
            "source_record_id source_word_ordinal coptic_lxx_ref_id "
            "coptic_lxx_ref_status", silent="deep"
        )
        greek = Fabric(
            locations=[str(greek_parent), str(modules / "lxx")],
            silent="deep",
        ).load("coptic_lxx_ref_id book chapter verse", silent="deep")
        assert coptic and greek

        # Both original Coptic editions of Jonah 2:1 are distinct physical
        # witnesses. They join via one *Greek verse address*, never node IDs.
        jonah = find_coptic_witnesses(coptic, greek, "Jonah", 2, 1)
        assert jonah.lxx_node == 679992
        assert jonah.declared_coptic_source_span_count is None
        assert len(jonah.spans) == 2
        assert {s.source_record_id for s in jonah.spans} == {
            "sahidic.jonah/sahidic.jonah:Jonah_02",
            "bohairic-jonah/bohairic.jonah:bohairic.Jonah_02",
        }
        assert all(
            s.status == "reference_candidate"
            and s.word_nodes and s.source_word_ordinals
            and len(s.word_nodes) == len(s.source_word_ordinals)
            for s in jonah.spans
        )
        for book, expected_node in (("Ruth", 663156), ("Hab", 680109)):
            result = find_coptic_witnesses(coptic, greek, book, 2, 1)
            assert result.lxx_node == expected_node
            assert len(result.spans) == 1, (book, result)
            assert result.spans[0].source_word_ordinals[0] >= 1

        print(json.dumps({
            "status": "PASS",
            "source": COPTIC_PIN,
            "greek": LXX_PIN,
            "source_records": len(docs),
            "candidate_lxx_verses": produced.lxx_candidate_verses,
            "jonah_distinct_coptic_witnesses": len(jonah.spans),
            "jonah_native_lxx_verse_node": jonah.lxx_node,
            "optional_greek_span_count_absent": True,
            "interpretation": "address candidates only; no textual word alignment",
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue130_real_witnesses.py COPTIC_ROOT LXX_TF")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
