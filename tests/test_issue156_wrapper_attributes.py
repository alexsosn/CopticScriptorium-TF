"""#156: RED-first source-literal gap/supplied/abbr multi-attribute model."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, graph_fingerprint, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def parse(body: str):
    return parse_tt_record(
        ('<meta corpus="sahidic.ot"><norm_group norm_group="fixture">'
         + body + '</norm_group>').encode("utf-8"),
        source_record_id="sahidic.ot/sahidic.ot:01_Genesis_01",
        source_path="sahidic.ot/sahidic.ot_TT.zip!01_Genesis_01.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
        packaging="archive",
    )


def norm(word: int, content: str):
    return (f'<norm xml:id="u{word}" norm="form{word}" '
            + ('new_sent="true" func="root"' if word == 1 else 'func="obj" head="#u1"')
            + f'>{content}</norm>')


class ExactSourceAttributes(unittest.TestCase):
    def test_all_three_original_tags_keep_distinct_literal_attributes(self):
        doc = parse(
            norm(1, 'a<gap extent="2" reason="lost" unit="character">b</gap>'
                 '<supplied source="scribe" reason="lacuna">c</supplied>'
                 '<abbr type="nomina_sacra">d</abbr>e')
        )
        self.assertEqual(len(doc.words), 1)
        self.assertEqual(
            [(a.kind, a.attributes, a.word_ordinals, a.start_char, a.end_char)
             for a in doc.editorial_annotations],
            [
                ("gap", (("extent", "2"), ("reason", "lost"), ("unit", "character")), (), 1, 2),
                ("supplied", (("reason", "lacuna"), ("source", "scribe")), (), 2, 3),
                ("abbr", (("type", "nomina_sacra"),), (), 3, 4),
            ],
        )

    def test_crossed_source_wrappers_and_present_empty_are_distinguishable(self):
        d = parse(
            '<gap extent="" reason="lost">'
            '<supplied source="editor">' + norm(1, "a")
            + '</gap>' + norm(2, "b") + '</supplied>'
            '<abbr type="">'
            + norm(3, "c") + '</abbr>'
        )
        a = d.editorial_annotations
        self.assertEqual([x.kind for x in a], ["gap", "supplied", "abbr"])
        self.assertEqual(a[0].attributes, (("extent", ""), ("reason", "lost")))
        self.assertEqual(a[0].word_ordinals, (1,))
        self.assertEqual(a[1].word_ordinals, (1, 2))
        self.assertEqual(a[2].word_ordinals, (3,))
        self.assertEqual(a[2].attributes, (("type", ""),))

    def test_absent_primary_attribute_is_not_forged(self):
        d = parse('<abbr type="nomina_sacra">' + norm(1, "x") + '</abbr>')
        self.assertEqual(d.editorial_annotations[0].attributes, (("type", "nomina_sacra"),))
        self.assertIsNone(dict(d.editorial_annotations[0].attributes).get("abbr"))

    def test_duplicate_or_orphan_and_unclosed_tags_fail_closed(self):
        for kind in ("gap", "supplied", "abbr"):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(ValueError, "duplicate tag attribute"):
                    parse(f'<{kind} type="a" type="b">' + norm(1, "x") + f'</{kind}>')
                with self.assertRaisesRegex(ValueError, "without opening"):
                    parse('</' + kind + '>' + norm(1, "x"))
                with self.assertRaisesRegex(ValueError, "unclosed"):
                    parse('<' + kind + ' type="x">' + norm(1, "x"))

    def test_native_scalar_reloads_with_exact_keys_without_any_new_word_slot(self):
        d = parse(
            norm(1,'a<gap extent="2" reason="lost" unit="character">b</gap>'
                 '<supplied source="scribe" reason="lacuna">c</supplied>'
                 '<abbr type="nomina_sacra">d</abbr>')
        )
        graph = build_graph([d])
        self.assertFalse(validate_graph(graph))
        self.assertEqual(len(graph.slots), 1)
        native = {node.otype: node for node in graph.nodes
                  if node.otype in {"gap","supplied","abbr"}}
        self.assertEqual(native["gap"].source_attributes,
                         (("extent","2"),("reason","lost"),("unit","character")))
        with TemporaryDirectory() as tmp:
            tfdir = Path(tmp)/"tf"
            write_graph(graph, tfdir)
            for feature in (
                "tt_attr_gap_extent", "tt_attr_gap_reason",
                "tt_attr_gap_unit", "tt_attr_supplied_source",
                "tt_attr_supplied_reason", "tt_attr_abbr_type",
            ):
                self.assertTrue((tfdir / (feature+".tf")).is_file(), feature)
            api = Fabric(locations=[str(tfdir)], silent="deep").load(
                "tt_attr_gap_extent tt_attr_gap_reason tt_attr_gap_unit "
                "tt_attr_supplied_source tt_attr_supplied_reason tt_attr_abbr_type",
                silent="deep",
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 1)
            self.assertEqual(api.F.tt_attr_gap_extent.v(api.F.otype.s("gap")[0]), "2")
            self.assertEqual(api.F.tt_attr_gap_unit.v(api.F.otype.s("gap")[0]), "character")
            self.assertEqual(api.F.tt_attr_abbr_type.v(api.F.otype.s("abbr")[0]), "nomina_sacra")
            self.assertIsNone(api.F.tt_attr_gap_extent.v(api.F.otype.s("abbr")[0]))

    def test_public_graph_validator_rejects_forged_duplicate_attributes(self):
        doc = parse('<gap reason="lost">'+norm(1,"a")+'</gap>')
        graph = build_graph([doc])
        original = next(node for node in graph.nodes if node.otype == "gap")
        corrupt = replace(
            original, source_attributes=(("reason", "lost"), ("reason", "forged"))
        )
        forged = replace(
            graph,
            nodes=tuple(corrupt if n.id == original.id else n for n in graph.nodes),
        )
        self.assertTrue(
            any("source attributes" in message for message in validate_graph(forged))
        )

    def test_attributes_change_graph_fingerprint(self):
        one = build_graph([parse('<gap reason="lost">'+norm(1,"a")+'</gap>')])
        two = build_graph([parse('<gap reason="restored">'+norm(1,"a")+'</gap>')])
        self.assertNotEqual(graph_fingerprint(one), graph_fingerprint(two))


if __name__ == "__main__":
    unittest.main()
