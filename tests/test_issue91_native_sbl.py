"""Issue #91 RED: SBL Greek/Apparatus native TF source-conservation contract."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
REC = "sahidica.mark/sahidica.mark:Mark_02"


def parse(text):
    return parse_tt_record(
        text.encode("utf-8"),
        source_record_id=REC,
        source_path="sahidica.mark/sahidica.mark_TT/Mark_02.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=COMMIT,
    )


def norm(i, text, *, sentence=False):
    start = ' new_sent="true"' if sentence else ""
    return (f'<norm_group norm_group="{text}"><norm xml:id="u{i}" '
            f'func="root" norm="{text}"{start}>{text}</norm></norm_group>')


class SblAnnotationsTests(unittest.TestCase):
    def test_crossed_closures_are_independent_source_occurrences(self):
        raw = (
            '<meta corpus="sahidica.mark" chapter="2" Greek_source="SBL Greek New Testament">'
            '<verse_n verse_n="1"><sbl_apparatus sbl_apparatus="α WH ] β RP">'
            '<sbl_greek sbl_greek="Καὶ ⸀λόγος· ">'
            + norm(1, "ⲁ", sentence=True) + norm(2, "ⲃ") +
            '</sbl_apparatus></sbl_greek></verse_n>'
        )
        doc = parse(raw)
        self.assertEqual(len(doc.words), 2)
        self.assertEqual(
            [(a.kind, a.value, a.word_ordinals, a.source_verse_n) for a in doc.sbl_annotations],
            [
                ("sbl_apparatus", "α WH ] β RP", (1, 2), "1"),
                ("sbl_greek", "Καὶ ⸀λόγος· ", (1, 2), "1"),
            ],
        )
        graph = build_graph([doc])
        self.assertEqual(validate_graph(graph), ())
        self.assertEqual(len(graph.slots), 2)
        self.assertEqual([n.otype for n in graph.nodes if n.otype.startswith("sbl_")],
                         ["sbl_greek", "sbl_apparatus"])
        with TemporaryDirectory() as directory:
            dest = Path(directory) / "tf"
            write_graph(graph, dest)
            api = Fabric(locations=[str(dest)], silent="deep").load(
                "value render_mode source_record_id sbl_verse_n "
                "start_after_word_ordinal end_after_word_ordinal", silent="deep")
            self.assertTrue(api)
            greek = tuple(api.F.otype.s("sbl_greek"))
            app = tuple(api.F.otype.s("sbl_apparatus"))
            self.assertEqual((len(greek), len(app)), (1, 1))
            self.assertEqual(api.F.value.v(greek[0]), "Καὶ ⸀λόγος· ")
            self.assertEqual(api.F.value.v(app[0]), "α WH ] β RP")
            self.assertEqual(api.F.sbl_verse_n.v(greek[0]), "1")
            self.assertEqual(api.L.d(greek[0], otype="word"), (1, 2))
            self.assertEqual(api.F.source_record_id.v(greek[0]), REC)

    def test_present_empty_value_is_distinct_from_absent_tag(self):
        raw = '<meta corpus="a">' + (
            '<sbl_apparatus sbl_apparatus="">'
            + norm(1, "a", sentence=True) + '</sbl_apparatus>'
        )
        doc = parse(raw)
        self.assertEqual([(a.kind, a.value) for a in doc.sbl_annotations],
                         [("sbl_apparatus", "")])
        self.assertEqual(parse('<meta corpus="a">' + norm(1, "a", sentence=True)).sbl_annotations, ())

    def test_split_midword_annotation_retains_boundary_offsets_without_extra_slot(self):
        raw = (
            '<meta corpus="a"><norm_group norm_group="abcd">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
            'a<sbl_greek sbl_greek="λόγος">bc</sbl_greek>d'
            '</norm></norm_group>'
        )
        doc = parse(raw)
        annotation, = doc.sbl_annotations
        self.assertEqual(annotation.word_ordinals, ())
        self.assertEqual((annotation.start_word_ordinal, annotation.start_char), (1, 1))
        self.assertEqual((annotation.end_word_ordinal, annotation.end_char), (1, 3))
        graph = build_graph([doc])
        self.assertEqual(validate_graph(graph), ())
        node, = [n for n in graph.nodes if n.otype == "sbl_greek"]
        self.assertEqual(node.render_mode, "sbl_anchor")
        self.assertEqual(node.slots, (1,))
        self.assertEqual((node.start_char, node.end_char), (1, 3))

    def test_midword_open_excludes_partial_first_word_from_span(self):
        raw = (
            '<meta corpus="a"><norm_group norm_group="abc">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="abc">'
            'a<sbl_greek sbl_greek="Greek">bc</norm></norm_group>'
            '<norm_group norm_group="d">'
            '<norm xml:id="u2" func="root" norm="d">d</norm></norm_group>'
            '</sbl_greek>'
        )
        doc = parse(raw)
        annotation, = doc.sbl_annotations
        self.assertEqual(annotation.start_char, 1)
        self.assertEqual(annotation.word_ordinals, (2,))
        graph = build_graph([doc])
        self.assertEqual(validate_graph(graph), ())
        node, = [n for n in graph.nodes if n.otype == "sbl_greek"]
        self.assertEqual(node.render_mode, "sbl_span")
        self.assertEqual(node.slots, (2,))

    def test_two_repeated_greek_annotations_preserve_order_and_distinct_values(self):
        raw = ('<meta corpus="a"><sbl_greek sbl_greek="first">'
               + norm(1, "a", sentence=True) +
               '</sbl_greek><sbl_greek sbl_greek="second">'
               + norm(2, "b") + '</sbl_greek>')
        doc = parse(raw)
        self.assertEqual([(a.ordinal, a.value, a.word_ordinals) for a in doc.sbl_annotations],
                         [(1, "first", (1,)), (2, "second", (2,))])

    def test_zero_length_marker_is_anchored_and_not_forged_span(self):
        raw = ('<meta corpus="a"><sbl_greek sbl_greek="x"></sbl_greek>'
               + norm(1, "a", sentence=True))
        graph = build_graph([parse(raw)])
        self.assertEqual(validate_graph(graph), ())
        node, = [n for n in graph.nodes if n.otype == "sbl_greek"]
        self.assertEqual(node.render_mode, "sbl_anchor")
        self.assertEqual(node.slots, (1,))
        self.assertEqual((node.start_after_word_ordinal, node.end_after_word_ordinal), (0, 0))

    def test_missing_attr_and_unclosed_annotation_fail_closed(self):
        for raw in (
            '<meta corpus="a"><sbl_greek>' + norm(1, "a", sentence=True) + '</sbl_greek>',
            '<meta corpus="a"><sbl_greek sbl_greek="x">' + norm(1, "a", sentence=True),
            '<meta corpus="a"></sbl_apparatus>' + norm(1, "a", sentence=True),
        ):
            with self.subTest(raw=raw[:45]), self.assertRaisesRegex(ValueError, "sbl_"):
                parse(raw)


if __name__ == "__main__":
    unittest.main()
