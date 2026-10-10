"""Real pinned dual weft-only Coptic↔Greek reference modules acceptance (#73)."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.writer import write_graph
from copticscriptorium_tf.lxx_module import (
    LXX_PIN, COPTIC_PIN, materialize_lxx_reference_modules,
)

SOURCE_ITEMS = (
    ("sahidic.ruth", "sahidic.ruth", "Ruth_02.tt"),
    ("sahidic.jonah", "sahidic.jonah", "Jonah_02.tt"),
    ("bohairic-habakkuk", "bohairic.habakkuk", "bohairic.Habakkuk_02.tt"),
)


def main(coptic_source: Path, greek_parent: Path) -> None:
    docs = []
    for corpus, dataset, filename in SOURCE_ITEMS:
        path = f"{corpus}/{dataset}_TT/{filename}"
        docs.append(
            parse_tt_record(
                (coptic_source / path).read_bytes(),
                source_record_id=f"{corpus}/{dataset}:{filename[:-3]}",
                source_path=path,
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit=COPTIC_PIN,
            )
        )

    with TemporaryDirectory(prefix="coptic-lxx-dual-") as temp:
        work = Path(temp)
        coptic_tf = work / "coptic-parent"
        write_graph(build_graph(docs), coptic_tf)
        coptic_api = Fabric(locations=[str(coptic_tf)], silent="deep").load(
            "source_record_id source_word_ordinal", silent="deep"
        )
        greek_api = Fabric(locations=[str(greek_parent)], silent="deep").load(
            "book chapter verse subverse", silent="deep"
        )
        assert coptic_api and greek_api
        result = materialize_lxx_reference_modules(
            documents=docs, coptic_api=coptic_api, lxx_api=greek_api,
            output_root=work / "modules",
            lxx_parent_commit=LXX_PIN,
            coptic_source_commit=COPTIC_PIN,
            coptic_parent_tf=coptic_tf,
            lxx_parent_tf=greek_parent,
        )
        assert result.source_documents == 3
        assert result.coptic_status_words == 2104
        assert result.lxx_candidate_verses == 54, result
        assert result.coptic_candidate_words > 1900, result

        coptic_module = work / "modules" / "coptic"
        greek_module = work / "modules" / "lxx"
        for module in (coptic_module, greek_module):
            assert (module / "coptic_lxx_ref_id.tf").is_file()
            assert not any((module / f"{f}.tf").exists() for f in ("otype","oslots","otext"))

        fresh_coptic = Fabric(
            locations=[str(coptic_tf), str(coptic_module)], silent="deep"
        ).load(
            "source_record_id source_word_ordinal coptic_lxx_ref_id "
            "coptic_lxx_ref_status coptic_lxx_ref_evidence",
            silent="deep",
        )
        fresh_greek = Fabric(
            locations=[str(greek_parent), str(greek_module)], silent="deep"
        ).load("coptic_lxx_ref_id book chapter verse", silent="deep")
        assert fresh_coptic and fresh_greek
        assert fresh_coptic.F.otype.maxSlot == 2104
        assert fresh_greek.F.otype.maxSlot == 623693

        coptic_keys: Counter[str] = Counter()
        for word in fresh_coptic.F.otype.s("word"):
            status = fresh_coptic.F.coptic_lxx_ref_status.v(word)
            assert status is not None
            key = fresh_coptic.F.coptic_lxx_ref_id.v(word)
            if key:
                assert status == "reference_candidate", (word, key, status)
                coptic_keys[key] += 1

        greek_keys: dict[str,int] = {}
        for verse in fresh_greek.F.otype.s("verse"):
            key = fresh_greek.F.coptic_lxx_ref_id.v(verse)
            if key:
                assert key not in greek_keys
                greek_keys[key] = verse
        assert len(greek_keys) == 54
        assert set(coptic_keys) == set(greek_keys), (
            "the two parent-specific modules disagree on a shared reference"
        )
        assert coptic_keys["CenterBLC/LXX:1935:Ruth:2:1"] > 0
        assert greek_keys["CenterBLC/LXX:1935:Ruth:2:1"] == 663156
        print(json.dumps({
            "stage": "pinned-native-bilateral-reference-modules",
            "coptic_records": 3,
            "coptic_slots": 2104,
            "coptic_candidate_words": result.coptic_candidate_words,
            "coptic_status_words": result.coptic_status_words,
            "distinct_greek_verse_nodes": result.lxx_candidate_verses,
            "greek_commit": LXX_PIN,
            "coptic_source_commit": COPTIC_PIN,
            "scope": "reference_address_candidates_only_no_textual_word_equivalence",
        }, sort_keys=True), flush=True)
        print("PASS two native parent-specific Coptic/LXX weft modules reload and shared-ID join")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue73_dual_modules.py COPTIC_ROOT LXX_TF")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
