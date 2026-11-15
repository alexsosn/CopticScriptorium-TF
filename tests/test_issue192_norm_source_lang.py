"""#192 RED: original <norm lang="..."> is word-level source evidence.

The original lang attr is not the independent <lang> wrapper, morphological
morph.lang source attribute, or language inferred by semantic analysis.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
SOURCE = (
    '<meta corpus="fixture"><norm_group norm_group="one">'
    '<norm xml:id="u1" new_sent="true" func="root" norm="abc" lang="G&amp;L">'
    'a<lang lang="Latin">bc</lang></norm>'
    '<norm xml:id="u2" func="dep" head="#u1" norm="d" lang="">d</norm>'
    '<norm xml:id="u3" func="dep" head="#u1" norm="e">e</norm>'
    '</norm_group>'
)


def source_doc(source=SOURCE):
    return parse_tt_record(
        source.encode("utf-8"),
        source_record_id="fixture/fixture:wordlang", source_path="fixture/fixture_TT/wordlang.tt",
        upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN,
    )


class OriginalWordLanguageTests(unittest.TestCase):
    def test_parser_retains_original_word_lang_separate_from_inner_lang_tag(self):
        doc = source_doc()
        self.assertEqual(len(doc.words), 3)
        self.assertEqual([w.original_lang for w in doc.words], ["G&L", "", None])
        self.assertEqual([w.norm for w in doc.words], ["abc", "d", "e"])
        self.assertEqual([w.source_text for w in doc.words], ["abc", "d", "e"])
        self.assertEqual([w.dependency_head_ordinal for w in doc.words], [0, 1, 1])
        self.assertEqual(len(doc.language_annotations), 1)
        self.assertEqual(doc.language_annotations[0].value, "Latin")
        self.assertEqual(doc.language_annotations[0].word_ordinals, ())

    def test_exact_native_word_feature_and_document_locus(self):
        graph = build_graph((source_doc(),))
        self.assertFalse(validate_graph(graph))
        self.assertEqual(len(graph.slots), 3)
        self.assertEqual([s.original_lang for s in graph.slots], ["G&L", "", None])
        with TemporaryDirectory() as temp:
            output = write_graph(graph, Path(temp) / "tf")
            self.assertTrue((output / "source_attr_norm_lang.tf").is_file())
            api = Fabric(locations=[str(output)], silent="deep").load(
                "source_attr_norm_lang source_record_id source_word_ordinal norm",
                silent="deep",
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 3)
            self.assertEqual(
                [api.F.source_attr_norm_lang.v(n) for n in range(1, 4)],
                ["G&L", "", None],
            )
            self.assertEqual([api.F.norm.v(n) for n in range(1, 4)], ["abc", "d", "e"])
            self.assertEqual(api.T.nodeFromSection(("fixture/fixture:wordlang",)),
                             api.F.otype.s("document")[0])
            self.assertFalse(list(output.glob("*.json")) + list(output.glob("*.xml")))

    def test_duplicate_original_word_attributes_fail_closed(self):
        source = SOURCE.replace('norm="abc" lang="G&amp;L"', 'norm="abc" lang="A" lang="B"')
        with self.assertRaisesRegex(ValueError, "duplicate tag attribute"):
            source_doc(source)

    def test_full_source_release_gate_checks_original_values(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/issue69-full-verse-census.yml").read_text(
            encoding="utf-8"
        )
        source_test = (root / "tests/live_issue192_norm_lang_parity.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("live_issue192_norm_lang_parity.py pinned-coptic", workflow)
        self.assertIn("--native", workflow)
        self.assertIn("source_attr_norm_lang", source_test)
        self.assertIn("57_369", source_test)
        self.assertIn("source_sha256", source_test)
        self.assertNotIn("print(raw)", source_test)


if __name__ == "__main__":
    unittest.main()
