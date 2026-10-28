"""#189: original morph.lang stays distinct from enclosing <lang> annotation."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
HEAD = ('<meta corpus="fixture"><norm_group norm_group="sample">'
        '<norm xml:id="u1" new_sent="true" func="root" norm="abcdef">')
TAIL = '</norm></norm_group>'


def parse(body: str):
    return parse_tt_record(
        (HEAD + body + TAIL).encode("utf-8"),
        source_record_id="fixture/fixture:one",
        source_path="fixture/fixture_TT/one.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )


class MorphLangOriginalAttributeTests(unittest.TestCase):
    def test_parser_distinguishes_attribute_and_crossed_lang_annotation(self):
        doc = parse(
            'a<morph morph="bc" lang="Greek">'
            '<lang lang="Latin">bc</morph>d</lang>ef'
        )
        self.assertEqual(len(doc.words), 1)
        self.assertEqual(len(doc.token_annotations), 1)
        self.assertEqual(len(doc.language_annotations), 1)
        morph = doc.token_annotations[0]
        self.assertEqual(morph.source_attributes, (("lang", "Greek"), ("morph", "bc")))
        self.assertEqual((morph.ordinal, morph.value, morph.start_char, morph.end_char),
                         (1, "bc", 1, 3))
        self.assertEqual(doc.language_annotations[0].value, "Latin")
        self.assertEqual((doc.language_annotations[0].start_char,
                          doc.language_annotations[0].end_char), (1, 4))

    def test_absent_and_empty_original_attributes_keep_same_morph_slots(self):
        doc = parse(
            '<morph morph="a" lang="">a</morph>'
            '<morph morph="b">b</morph>'
            '<morph morph="c" lang="Greek">c</morph>def'
        )
        self.assertEqual(
            [a.source_attributes for a in doc.token_annotations],
            [(("lang", ""), ("morph", "a")), (), (("lang", "Greek"), ("morph", "c"))],
        )
        graph = build_graph((doc,))
        self.assertFalse(validate_graph(graph))
        nodes = [n for n in graph.nodes if n.otype == "morph"]
        self.assertEqual([n.slots for n in nodes], [(1,), (1,), (1,)])
        self.assertEqual([n.source_ordinal for n in nodes], [1, 2, 3])
        with TemporaryDirectory() as tmp:
            target = write_graph(graph, Path(tmp) / "tf")
            self.assertTrue((target / "source_attr_morph_lang.tf").exists())
            api = Fabric(locations=[str(target)], silent="deep").load(
                "source_attr_morph_lang source_ordinal source_record_id value",
                silent="deep",
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 1)
            native = api.F.otype.s("morph")
            self.assertEqual([api.F.source_attr_morph_lang.v(n) for n in native],
                             ["", None, "Greek"])
            self.assertEqual([api.F.value.v(n) for n in native], ["a", "b", "c"])
            self.assertEqual([api.F.source_ordinal.v(n) for n in native], [1, 2, 3])
            self.assertFalse(list(target.glob("*.xml")) + list(target.glob("*.json")))

    def test_unexpected_original_morph_keys_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "morph.*attributes|unexpected"):
            parse('<morph morph="a" fabricated="fake">a</morph>bcdef')
        with self.assertRaisesRegex(ValueError, "morph.*attributes|unexpected"):
            parse('<morph lang="Greek">a</morph>bcdef')

    def test_pinned_source_full_native_gate_is_required(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/issue69-full-verse-census.yml").read_text(encoding="utf-8")
        runner = (root / "tests/live_issue189_morph_lang_parity.py").read_text(encoding="utf-8")
        self.assertIn("live_issue189_morph_lang_parity.py pinned-coptic", workflow)
        self.assertIn("--native", workflow)
        self.assertIn("source_attr_morph_lang", runner)
        self.assertIn("284", runner)
        self.assertIn("source_sha256", runner)
        self.assertNotIn("print(raw)", runner)


if __name__ == "__main__":
    unittest.main()
