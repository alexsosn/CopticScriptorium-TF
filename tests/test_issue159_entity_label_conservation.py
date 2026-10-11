"""RED-first lossless nine-family TT entity/name-label conservation (#159).

These original source labels are *not* ontology identities or necessarily
attributes of the nearest entity; only their source positions are asserted.
"""
from __future__ import annotations

from pathlib import Path
from dataclasses import replace
from tempfile import TemporaryDirectory
import unittest

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph
from tf.fabric import Fabric

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS = (
    "entity_head_tok", "entity_text", "entity_identity", "persName_type",
    "placeName_type", "placeName_ref", "roleName_type", "rs_type", "org_type",
)
VALUES = ("#u1", "source string", "Sarah", "monk", "city_village",
          "paths:places:32", "religious", "object", "ethnic")


def parse(text: str):
    return parse_tt_record(
        text.encode("utf-8"),
        source_record_id="demo/demo:one",
        source_path="demo/demo_TT/one.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )


class EntityLabelsNativeTFTests(unittest.TestCase):
    def test_all_nine_literal_kinds_are_distinct_natively_queryable_nodes(self):
        wrappers = "".join(f'<{tag} {tag}="{value}">' for tag, value in zip(KINDS, VALUES))
        ends = "".join(f'</{tag}>' for tag in reversed(KINDS))
        raw = (
            '<meta corpus="demo">'
            '<norm_group norm_group="one">'
            '<norm xml:id="u1" new_sent="true" func="root" lemma="a" norm="a">'
            + wrappers + "a" + ends + '</norm></norm_group>'
        )
        d = parse(raw)
        self.assertEqual(
            [(x.kind, x.value) for x in d.entity_label_annotations],
            list(zip(KINDS, VALUES)),
        )
        self.assertEqual(len(d.words), 1)
        g = build_graph((d,))
        self.assertEqual(len(g.slots), 1)
        self.assertEqual([n.otype for n in g.nodes if n.otype in KINDS], list(KINDS))
        self.assertTrue(all(n.render_mode == "entity_label_anchor"
                            for n in g.nodes if n.otype in KINDS))
        with TemporaryDirectory() as temp:
            tf_dir = Path(temp) / "tf"
            write_graph(g, tf_dir)
            api = Fabric(locations=[str(tf_dir)], silent="deep").load(
                "value render_mode source_record_id start_word_ordinal start_char"
                " end_word_ordinal end_char source_ordinal", silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 1)
            for kind, value in zip(KINDS, VALUES):
                (node,) = api.F.otype.s(kind)
                self.assertEqual(api.F.value.v(node), value)
                self.assertEqual(api.F.source_record_id.v(node), d.source_record_id)
                self.assertEqual(api.F.render_mode.v(node), "entity_label_anchor")
                self.assertEqual(api.F.start_word_ordinal.v(node), 1)
                self.assertEqual(api.F.start_char.v(node), 0)
                self.assertEqual(api.L.d(node, otype="word"), (1,))

    def test_crossed_closings_keep_original_source_coordinates_not_forged_entity_edges(self):
        raw = (
            '<meta corpus="demo">'
            '<norm_group norm_group="x"><norm xml:id="u1" new_sent="true" norm="abc">'
            '<placeName_ref placeName_ref="paths:places:32">'
            '<placeName_type placeName_type="city_village">ab'
            '</placeName_ref>c</placeName_type>'
            '</norm></norm_group>'
            '<norm_group norm_group="y"><norm xml:id="u2" new_sent="true" norm="z">z</norm></norm_group>'
        )
        d = parse(raw)
        self.assertEqual(
            [(a.kind, a.value, a.start_char, a.end_char)
             for a in d.entity_label_annotations],
            [("placeName_ref", "paths:places:32", 0, 2),
             ("placeName_type", "city_village", 0, 3)],
        )
        g = build_graph([d])
        self.assertEqual(len(g.slots), 2)
        nodes = [n for n in g.nodes if n.otype in {"placeName_ref", "placeName_type"}]
        self.assertTrue(all(n.render_mode == "entity_label_anchor" for n in nodes))
        self.assertFalse(any(e.kind.startswith("entity_label") for e in g.edges))

    def test_whole_source_word_span_vs_token_internal_anchor(self):
        raw = (
            '<meta corpus="demo"><roleName_type roleName_type="religious">'
            '<norm_group norm_group="x"><norm xml:id="u1" new_sent="true" norm="x">x</norm>'
            '<norm xml:id="u2" new_sent="true" norm="y">y</norm>'
            '</norm_group></roleName_type>'
        )
        d = parse(raw)
        a, = d.entity_label_annotations
        self.assertEqual(a.word_ordinals, (1, 2))
        g = build_graph([d])
        node, = (n for n in g.nodes if n.otype == "roleName_type")
        self.assertEqual(node.render_mode, "entity_label_span")
        self.assertEqual(node.slots, (1, 2))

    def test_adversarial_corrupt_entity_label_node_is_rejected_by_graph_validator(self):
        raw = (
            '<meta corpus="demo"><norm_group norm_group="one">'
            '<norm xml:id="u1" new_sent="true" norm="a">'
            '<entity_identity entity_identity="Sarah">a</entity_identity>'
            '</norm></norm_group>'
        )
        graph = build_graph((parse(raw),))
        target = next(n for n in graph.nodes if n.otype == "entity_identity")
        bad = replace(
            graph, nodes=tuple(
                replace(n, render_mode="false_ontology_link")
                if n.id == target.id else n for n in graph.nodes
            )
        )
        self.assertTrue(any(
            "entity label" in error and "precise span/anchor" in error
            for error in validate_graph(bad)
        ))

    def test_identical_source_name_labels_do_not_merge_distinct_entity_mentions(self):
        raw = (
            '<meta corpus="demo">'
            '<entity entity="person" head_tok="#u1" identity="person-A">'
            '<norm_group norm_group="x">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="a">'
            '<entity_identity entity_identity="Sarah">a</entity_identity>'
            '</norm></norm_group></entity>'
            '<entity entity="person" head_tok="#u2" identity="person-B">'
            '<norm_group norm_group="y">'
            '<norm xml:id="u2" new_sent="true" func="root" norm="b">'
            '<entity_identity entity_identity="Sarah">b</entity_identity>'
            '</norm></norm_group></entity>'
        )
        document = parse(raw)
        self.assertEqual([a.value for a in document.entity_label_annotations],
                         ["Sarah", "Sarah"])
        graph = build_graph((document,))
        self.assertEqual(len(graph.slots), 2)
        self.assertEqual(len([n for n in graph.nodes if n.otype == "entity"]), 2)
        source_labels = [n for n in graph.nodes if n.otype == "entity_identity"]
        self.assertEqual(len(source_labels), 2)
        self.assertNotEqual(source_labels[0].slots, source_labels[1].slots)
        self.assertFalse(any(e.kind.startswith("ontology") or
                             e.kind.startswith("entity_label") for e in graph.edges))

    def test_malformed_missing_unclosed_and_orphan_source_annotations_fail_closed(self):
        base = '<meta corpus="demo"><norm_group norm_group="x"><norm xml:id="u1" new_sent="true" norm="x">'
        end = 'x</norm></norm_group>'
        for content, message in (
            ('<entity_identity>x</entity_identity>', "has no source value"),
            ('<entity_identity entity_identity="Sarah">x', "unclosed entity label"),
            ('</entity_identity>x', "closing entity label annotation without opening"),
        ):
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, message):
                    parse(base + content + end)


if __name__ == "__main__":
    unittest.main()
