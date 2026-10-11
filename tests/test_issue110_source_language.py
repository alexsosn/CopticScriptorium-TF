"""RED-first source language wrapper conservation contract (#110).

Language annotations come from upstream Coptic TT. Do not conflate them with
SBL Greek NT passages, Greek loanword certification, or Text-Fabric slots.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph
from tf.fabric import Fabric

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def parse(source: str):
    return parse_tt_record(
        source.encode("utf-8"),
        source_record_id="sahidica.mark/sahidica.mark:Mark_02",
        source_path="sahidica.mark/sahidica.mark_TT/Mark_02.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )


META = '<meta corpus="sahidica.mark" chapter="2">'


class NativeLanguageSourceSpanTests(unittest.TestCase):
    def test_inside_norm_retains_literal_and_character_span_not_forged_whole_word(self):
        doc = parse(
            META + '<norm_group norm_group="one">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="abcdef">'
            'ab<lang lang="Greek">cd</lang>ef</norm></norm_group>'
        )
        self.assertEqual(len(doc.words), 1)
        self.assertEqual(len(doc.language_annotations), 1)
        ann = doc.language_annotations[0]
        self.assertEqual((ann.kind, ann.value, ann.word_ordinals), ("lang", "Greek", ()))
        self.assertEqual(
            (ann.start_word_ordinal, ann.start_char,
             ann.end_word_ordinal, ann.end_char), (1, 2, 1, 4)
        )
        g = build_graph([doc])
        lang = next(n for n in g.nodes if n.otype == "lang")
        self.assertEqual(lang.slots, (1,))
        self.assertEqual(lang.value, "Greek")
        self.assertEqual(lang.render_mode, "lang_anchor")
        self.assertEqual((lang.start_char, lang.end_char), (2, 4))

    def test_whole_word_wrapper_has_true_two_word_locus(self):
        doc = parse(
            META + '<norm_group norm_group="ab"><lang lang="Hebrew">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="a">a</norm>'
            '<norm xml:id="u2" new_sent="true" func="root" norm="b">b</norm>'
            '</lang></norm_group>'
        )
        self.assertEqual(doc.language_annotations[0].word_ordinals, (1, 2))
        g = build_graph([doc])
        n = next(n for n in g.nodes if n.otype == "lang")
        self.assertEqual(n.render_mode, "lang_span")
        self.assertEqual(n.slots, (1, 2))

    def test_sbl_occurrence_identity_is_unaffected_by_language_wrapper(self):
        doc = parse(
            META + '<norm_group norm_group="one">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="ab">'
            '<lang lang="Greek">a</lang>'
            '<sbl_greek sbl_greek="λογος">b</sbl_greek>'
            '<sbl_apparatus sbl_apparatus="reading">c</sbl_apparatus>'
            '<lang lang="Hebrew">d</lang>'
            '</norm></norm_group>'
        )
        self.assertEqual([a.ordinal for a in doc.sbl_annotations], [1, 2])
        self.assertEqual([a.kind for a in doc.sbl_annotations], ["sbl_greek", "sbl_apparatus"])
        self.assertEqual([a.ordinal for a in doc.language_annotations], [1, 2])
        self.assertEqual([a.value for a in doc.language_annotations], ["Greek", "Hebrew"])

    def test_malformed_language_lifecycle_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "closing.*lang"):
            parse(META + '<norm_group norm_group="x">'
                  '<norm xml:id="u1" new_sent="true" func="root" norm="a">'
                  '</lang>a</norm></norm_group>')
        with self.assertRaisesRegex(ValueError, "unclosed.*lang"):
            parse(META + '<norm_group norm_group="x">'
                  '<norm xml:id="u1" new_sent="true" func="root" norm="a">'
                  '<lang lang="Greek">a</norm></norm_group>')
        with self.assertRaisesRegex(ValueError, "lang.*no source value"):
            parse(META + '<norm_group norm_group="x">'
                  '<norm xml:id="u1" new_sent="true" func="root" norm="a">'
                  '<lang>a</lang></norm></norm_group>')
        doc = parse(
            META + '<norm_group norm_group="x">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="a">'
            '<lang lang="">a</lang></norm></norm_group>'
        )
        self.assertEqual(doc.language_annotations[0].value, "")

    def test_native_tf_reload_has_source_lang_nodes_and_char_positions(self):
        doc = parse(
            META + '<norm_group norm_group="ab">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="ab">'
            'a<lang lang="Greek">b</lang></norm>'
            '<norm xml:id="u2" new_sent="true" func="root" norm="xy">'
            '<lang lang="Hebrew">xy</lang></norm></norm_group>'
        )
        graph = build_graph([doc])
        with TemporaryDirectory() as root:
            path = Path(root) / "tf"
            write_graph(graph, path)
            api = Fabric(locations=[str(path)], silent="deep").load(
                "value render_mode start_char end_char source_record_id", silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 2)
            self.assertEqual(len(api.F.otype.s("document")), 1)
            nodes = api.F.otype.s("lang")
            self.assertEqual(len(nodes), 2)
            self.assertEqual([api.F.value.v(n) for n in nodes], ["Greek", "Hebrew"])
            self.assertEqual([api.F.render_mode.v(n) for n in nodes],
                             ["lang_anchor", "lang_anchor"])
            self.assertEqual([api.F.start_char.v(n) for n in nodes], [1, 0])
            self.assertEqual([api.F.end_char.v(n) for n in nodes], [2, 2])


if __name__ == "__main__":
    unittest.main()
