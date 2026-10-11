"""Issue #135 RED-first contract: preserve five token-internal scholarly TT wrappers."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph


META = '<meta corpus="fixture">'
PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS = ("morph", "norm_func", "norm_head", "norm_xml:id", "norm_new_sent")


def parse(source: str):
    return parse_tt_record(
        source.encode("utf-8"),
        source_record_id="fixture/fixture:one",
        source_path="fixture/fixture_TT/one.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )


def norm(text: str, visible: str = "abcdef") -> str:
    return (
        META + '<norm_group norm_group="test">'
        f'<norm xml:id="u1" new_sent="true" func="root" norm="{visible}">'
        + text + '</norm></norm_group>'
    )


class TokenSourceTests(unittest.TestCase):
    def test_crossed_norm_source_tags_are_independent_occurrences(self):
        doc = parse(norm(
            '<norm_new_sent norm_new_sent="true">'
            '<norm_head norm_head="#u1">'
            '<norm_func norm_func="root">'
            '<norm_xml:id norm_xml:id="u1">'
            'ab</norm_new_sent>cd</norm_head>e</norm_func>f</norm_xml:id>'
        ))
        self.assertEqual(len(doc.words), 1)
        self.assertEqual(tuple(a.kind for a in doc.token_annotations),
                         ("norm_new_sent", "norm_head", "norm_func", "norm_xml:id"))
        self.assertEqual(tuple(a.ordinal for a in doc.token_annotations), (1, 2, 3, 4))
        self.assertEqual(tuple((a.start_char, a.end_char) for a in doc.token_annotations),
                         ((0, 2), (0, 4), (0, 5), (0, 6)))
        self.assertEqual(tuple(a.value for a in doc.token_annotations),
                         ("true", "#u1", "root", "u1"))
        self.assertTrue(all(a.word_ordinals == () for a in doc.token_annotations))

    def test_morph_lang_crossing_preserves_id_and_subword_positions(self):
        doc = parse(norm(
            'a<morph morph="bc"><lang lang="Greek">bc</morph>d</lang>ef'
        ))
        self.assertEqual([a.kind for a in doc.token_annotations], ["morph"])
        morph = doc.token_annotations[0]
        lang = doc.language_annotations[0]
        self.assertEqual((morph.start_char, morph.end_char), (1, 3))
        self.assertEqual((lang.start_char, lang.end_char), (1, 4))
        self.assertEqual((morph.value, lang.value), ("bc", "Greek"))
        g = build_graph([doc])
        self.assertFalse(validate_graph(g))
        native = next(n for n in g.nodes if n.otype == "morph")
        self.assertEqual(native.slots, (1,))
        self.assertEqual(native.render_mode, "token_annotation_anchor")
        self.assertEqual((native.start_char, native.end_char), (1, 3))

    def test_source_ordinal_tracks_openings_not_crossed_closures(self):
        doc = parse(norm(
            '<morph morph="ab">a<norm_func norm_func="root">b</morph>c</norm_func>def'
        ))
        self.assertEqual([(a.kind, a.ordinal) for a in doc.token_annotations],
                         [("morph", 1), ("norm_func", 2)])

    def test_sbl_identity_and_existing_tt_heads_are_unchanged(self):
        doc = parse(norm(
            '<sbl_greek sbl_greek="Greek-source">'
            'a<morph morph="b">b</sbl_greek>c</morph>'
            '<sbl_apparatus sbl_apparatus="note">def</sbl_apparatus>'
        ))
        self.assertEqual([(a.kind, a.ordinal) for a in doc.sbl_annotations],
                         [("sbl_greek", 1), ("sbl_apparatus", 2)])
        self.assertEqual(len(doc.token_annotations), 1)
        self.assertEqual(len(doc.words), 1)
        self.assertEqual(doc.words[0].dependency_head_ordinal, 0)

    def test_missing_value_and_unmatched_or_unclosed_tags_fail_closed(self):
        for name in KINDS:
            with self.subTest(tag=name):
                with self.assertRaisesRegex(ValueError, "no source value"):
                    parse(norm(f"<{name}>ab</{name}>cdef"))
                with self.assertRaisesRegex(ValueError, "closing|without opening"):
                    parse(norm(f"</{name}>abcdef"))
                with self.assertRaisesRegex(ValueError, "unclosed|inside norm"):
                    parse(norm(f"<{name} {name}=\"x\">abcdef"))
                with self.assertRaisesRegex(ValueError, "inside norm|outside norm"):
                    parse(META + f'<{name} {name}="x"></{name}>' +
                          norm("abcdef")[len(META):])

    def test_present_empty_value_and_real_native_tf_clean_reload(self):
        items = "".join(f'<{k} {k}=""><{k} {k}="v">a</{k}></{k}>' for k in KINDS)
        doc = parse(norm(items + "b", visible="aaaaab"))
        self.assertEqual(len(doc.token_annotations), 2 * len(KINDS))
        graph = build_graph([doc])
        self.assertFalse(validate_graph(graph))
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "tf"
            write_graph(graph, target)
            api = Fabric(locations=[str(target)], silent="deep").load(
                "value render_mode start_char end_char source_ordinal", silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 1)
            for kind in KINDS:
                nodes = api.F.otype.s(kind)
                self.assertEqual(len(nodes), 2)
                self.assertEqual([api.F.value.v(n) for n in nodes], ["", "v"])
                self.assertTrue(all(
                    api.F.render_mode.v(n) == "token_annotation_anchor" for n in nodes
                ))


if __name__ == "__main__":
    unittest.main()
