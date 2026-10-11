"""RED-first contract: independently loadable Coptic and LXX TF weft modules.

The same stable *reference candidate* ID connects separate native TF warps.
A shared book/chapter/verse address is NOT a certified textual alignment.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from copticscriptorium_tf.lxx_modules import (
    build_parent_word_index, compile_reference_projection,
    write_reference_modules,
)

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
ID = "CenterBLC/LXX:1935:Ruth:2:1"


def document(record: str, text: str):
    raw = (
        '<meta corpus="sahidic.ruth" chapter="2"'
        ' document_cts_urn="urn:cts:copticLit:ot.ruth.coptot_ed:2">'
        '<verse_n verse_n="1">'
        f'<norm_group norm_group="w"><norm xml:id="u1" new_sent="true"'
        f' func="root" norm="{text}">{text}</norm></norm_group>'
    )
    return parse_tt_record(
        raw.encode(), source_record_id=f"sahidic.ruth/sahidic.ruth:{record}",
        source_path=f"sahidic.ruth/sahidic.ruth_TT/{record}.tt",
        upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN,
    )


def fake_lxx(root: Path):
    parent = root / "lxx-parent"
    parent.mkdir()
    (parent / "otype.tf").write_text(
        "@node\n@valueType=str\n\n1-3\tword\n4\tverse\n", encoding="utf-8"
    )
    (parent / "oslots.tf").write_text(
        "@edge\n@valueType=str\n\n4\t1-3\n", encoding="utf-8"
    )
    (parent / "otext.tf").write_text(
        "@config\n@fmt:text-orig-full={word} \n\n", encoding="utf-8"
    )
    return parent


class NativeReferenceModuleTests(unittest.TestCase):
    def test_two_witnesses_same_shared_reference_and_two_real_tf_warps(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            documents = (document("Ruth_02a", "ⲁ"), document("Ruth_02b", "ⲃ"))
            write_graph(build_graph(documents), base / "coptic-parent")
            fake_lxx(base)
            api = Fabric(locations=[str(base / "coptic-parent")], silent="deep").load(
                "source_record_id source_word_ordinal", silent="deep"
            )
            self.assertTrue(api)
            reports = tuple(
                resolve_coptic_lxx_references(d, lookup=lambda b, c, v: 4)
                for d in documents
            )
            projection = compile_reference_projection(
                reports, build_parent_word_index(api),
                lookup=lambda b, c, v: 4,
                lxx_node_type=lambda n: "verse" if n == 4 else "word",
            )
            self.assertEqual(len(projection.coptic["coplxx_ref"]), 2)
            self.assertEqual(projection.lxx["coplxx_ref"], {4: ID})
            self.assertEqual(projection.lxx["coplxx_witness_count"], {4: 2})
            out = base / "modules"
            write_reference_modules(out, projection)
            for side in ("coptic", "lxx"):
                self.assertFalse((out / side / "otype.tf").exists())
                self.assertFalse((out / side / "oslots.tf").exists())
                self.assertFalse((out / side / "otext.tf").exists())
            coptic = Fabric(locations=str(base), modules=("coptic-parent", "modules/coptic"), silent="deep").load(
                "coplxx_ref coplxx_status", silent="deep"
            )
            lxx = Fabric(locations=str(base), modules=("lxx-parent", "modules/lxx"), silent="deep").load(
                "coplxx_ref coplxx_witness_count", silent="deep"
            )
            self.assertTrue(coptic)
            self.assertTrue(lxx)
            self.assertEqual([coptic.F.coplxx_ref.v(w) for w in (1, 2)], [ID, ID])
            self.assertEqual(lxx.F.coplxx_ref.v(4), ID)
            self.assertEqual(lxx.F.coplxx_witness_count.v(4), 2)
            self.assertEqual(coptic.F.otype.maxSlot, 2)
            self.assertEqual(lxx.F.otype.maxSlot, 3)
            self.assertEqual(len(tuple(out.rglob("*.tf"))), 6)

    def test_unknown_target_does_not_fabricate_cross_corpus_reference(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            d = document("Ruth_02a", "ⲁ")
            write_graph(build_graph((d,)), base / "coptic-parent")
            api = Fabric(locations=[str(base / "coptic-parent")], silent="deep").load(
                "source_record_id source_word_ordinal", silent="deep"
            )
            reports = (resolve_coptic_lxx_references(d, lookup=lambda *args: None),)
            proj = compile_reference_projection(
                reports, build_parent_word_index(api),
                lookup=lambda *args: None, lxx_node_type=lambda n: "verse",
            )
            self.assertEqual(proj.lxx, {})
            self.assertEqual(proj.coptic["coplxx_status"], {1: "unresolved"})
            self.assertNotIn("coplxx_ref", proj.coptic)

    def test_tampered_parent_node_or_missing_word_is_fail_closed(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            d = document("Ruth_02a", "ⲁ")
            write_graph(build_graph((d,)), base / "parent")
            api = Fabric(locations=[str(base / "parent")], silent="deep").load(
                "source_record_id source_word_ordinal", silent="deep"
            )
            report = (resolve_coptic_lxx_references(d, lookup=lambda *args: 4),)
            with self.assertRaisesRegex(ValueError, "parent"):
                compile_reference_projection(
                    report, {}, lookup=lambda *args: 4,
                    lxx_node_type=lambda n: "verse",
                )
            with self.assertRaisesRegex(ValueError, "target"):
                compile_reference_projection(
                    report, build_parent_word_index(api),
                    lookup=lambda *args: 5,
                    lxx_node_type=lambda n: "verse",
                )


if __name__ == "__main__":
    unittest.main()
