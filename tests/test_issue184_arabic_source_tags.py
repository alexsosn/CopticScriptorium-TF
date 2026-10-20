"""#184 RED: preserve original Arabic TT tag kind in native TF (not a new slot)."""
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
    '<meta corpus="fixture" title="Source Arabic kind">'
    '<norm_group norm_group="one"><arabic arabic="Arabic A">'
    '<norm xml:id="u1" new_sent="true" pos="N" func="root" lemma="a" norm="ⲁ">ⲁ</norm>'
    '</arabic></norm_group>'
    '<norm_group norm_group="two"><arabic_translation arabic_translation="Arabic B">'
    '<norm xml:id="u2" pos="V" func="dep" head="#u1" lemma="b" norm="ⲃ">ⲃ</norm>'
    '</arabic_translation></norm_group>'
)


def parse(s: str = SOURCE):
    return parse_tt_record(
        s.encode("utf-8"), source_record_id="fixture/fixture:arabic",
        source_path="fixture/fixture_TT/arabic.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )


class OriginalArabicTagConservationTests(unittest.TestCase):
    def test_parser_preserves_two_raw_source_tag_spellings(self):
        document = parse()
        self.assertEqual(len(document.words), 2)
        self.assertEqual(len(document.arabic_translations), 2)
        self.assertEqual(
            [a.source_tag for a in document.arabic_translations],
            ["arabic", "arabic_translation"],
        )
        self.assertEqual([a.text for a in document.arabic_translations],
                         ["Arabic A", "Arabic B"])
        self.assertEqual([a.word_ordinals for a in document.arabic_translations],
                         [(1,), (2,)])

    def test_graph_and_clean_native_tf_keep_kind_without_new_slots(self):
        graph = build_graph((parse(),))
        self.assertFalse(validate_graph(graph))
        nodes = [node for node in graph.nodes if node.otype == "arabic_translation"]
        self.assertEqual(len(nodes), 2)
        self.assertEqual([node.source_tag for node in nodes],
                         ["arabic", "arabic_translation"])
        self.assertEqual([node.slots for node in nodes], [(1,), (2,)])
        with TemporaryDirectory() as temp:
            output = write_graph(graph, Path(temp) / "tf")
            self.assertTrue((output / "original_source_tag.tf").is_file())
            api = Fabric(locations=[str(output)], silent="deep").load(
                "original_source_tag own_text source_record_id", silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 2)
            nodes = api.F.otype.s("arabic_translation")
            self.assertEqual(
                [api.F.original_source_tag.v(node) for node in nodes],
                ["arabic", "arabic_translation"],
            )
            self.assertEqual([api.T.text(node) for node in nodes], ["Arabic A", "Arabic B"])
            self.assertEqual(
                [tuple(api.E.oslots.s(node)) for node in nodes], [(1,), (2,)]
            )
            self.assertEqual(
                api.T.nodeFromSection(("fixture/fixture:arabic",)),
                api.F.otype.s("document")[0],
            )
            self.assertFalse(list(output.glob("*.json")) + list(output.glob("*.xml")))

    def test_full_pinned_source_parity_is_part_of_actual_release_gate(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/issue69-full-verse-census.yml").read_text(
            encoding="utf-8"
        )
        script = (root / "tests/live_issue184_arabic_source_parity.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("live_issue184_arabic_source_parity.py pinned-coptic", workflow)
        self.assertIn("--native", workflow)
        self.assertIn("AP.044.w670.temptation.tt", script)
        self.assertIn("AP.054.daniel.04.tt", script)
        self.assertIn("2_394_354", script)
        self.assertIn("original_source_tag", script)
        self.assertNotIn("print(source_text)", script)

    def test_independent_source_scanner_recognizes_actual_tag_openings(self):
        import runpy
        scanner = runpy.run_path(str(
            Path(__file__).resolve().parents[1] /
            "tests/live_issue184_arabic_source_parity.py"
        ))
        pattern = scanner["KIND_PATTERN"]
        source = (
            '<arabic arabic="first">'
            '<arabic_translation arabic_translation="second">'
        )
        self.assertEqual([match.group(1) for match in pattern.finditer(source)],
                         ["arabic", "arabic_translation"])
        attrs = scanner["ATTR_PATTERN"]
        self.assertEqual(attrs.findall(' arabic="first"'), [("arabic", "first")])

    def test_existing_english_translation_is_not_relabelled_arabic(self):
        source = SOURCE.replace(
            '<arabic arabic="Arabic A">', '<translation translation="English A">'
        ).replace('</arabic>', '</translation>')
        document = parse(source)
        self.assertEqual(len(document.translations), 1)
        self.assertEqual(len(document.arabic_translations), 1)
        graph = build_graph((document,))
        english = next(node for node in graph.nodes if node.otype == "translation")
        self.assertIsNone(english.source_tag)


if __name__ == "__main__":
    unittest.main()
