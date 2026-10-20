"""#187 RED: original <entity text="..."> attribute is independent source evidence."""
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
    '<meta corpus="fixture">'
    '<norm_group norm_group="abc">'
    '<entity entity="person" head_tok="#u1" text="S &amp; T">'
    '<norm xml:id="u1" new_sent="true" func="root" norm="a">a</norm>'
    '</entity>'
    '<entity entity="person" head_tok="#u2" text="">'
    '<norm xml:id="u2" func="dep" head="#u1" norm="b">b</norm>'
    '</entity>'
    '<entity entity="person" head_tok="#u3">'
    '<norm xml:id="u3" func="dep" head="#u1" norm="c">c</norm>'
    '</entity>'
    '</norm_group>'
)


def parsed():
    return parse_tt_record(
        SOURCE.encode("utf-8"),
        source_record_id="fixture/fixture:entity", source_path="fixture/fixture_TT/entity.tt",
        upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN,
    )


class OriginalEntityTextAttributeTests(unittest.TestCase):
    def test_parser_distinguishes_source_text_attribute_from_generated_word_text(self):
        d = parsed()
        self.assertEqual(len(d.words), 3)
        self.assertEqual(len(d.entities), 3)
        self.assertEqual([e.source_text_literal for e in d.entities], ["S & T", "", None])
        self.assertEqual([e.head_word_ordinal for e in d.entities], [1, 2, 3])
        self.assertEqual([e.word_ordinals for e in d.entities], [(1,), (2,), (3,)])

    def test_native_entity_source_attr_preserves_values_and_empty_presence(self):
        graph = build_graph((parsed(),))
        self.assertFalse(validate_graph(graph))
        nodes = [n for n in graph.nodes if n.otype == "entity"]
        self.assertEqual(
            [n.source_attributes for n in nodes],
            [(("text", "S & T"),), (("text", ""),), ()],
        )
        self.assertEqual([n.slots for n in nodes], [(1,), (2,), (3,)])
        with TemporaryDirectory() as tmp:
            output = write_graph(graph, Path(tmp) / "tf")
            self.assertTrue((output / "source_attr_entity_text.tf").is_file())
            api = Fabric(locations=[str(output)], silent="deep").load(
                "source_attr_entity_text source_record_id entity_class",
                silent="deep",
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 3)
            native = api.F.otype.s("entity")
            self.assertEqual([api.F.source_attr_entity_text.v(n) for n in native],
                             ["S & T", "", None])
            self.assertEqual([tuple(api.E.oslots.s(n)) for n in native],
                             [(1,), (2,), (3,)])
            self.assertEqual([api.F.entity_class.v(n) for n in native],
                             ["person", "person", "person"])
            self.assertEqual(api.T.nodeFromSection(("fixture/fixture:entity",)),
                             api.F.otype.s("document")[0])
            self.assertFalse(list(output.glob("*.json")) + list(output.glob("*.xml")))

    def test_standalone_entity_text_kind_is_not_an_entity_attribute(self):
        source = SOURCE.replace(
            '<entity entity="person" head_tok="#u1" text="S &amp; T">',
            '<entity entity="person" head_tok="#u1"><entity_text entity_text="label">'
        ).replace('</entity>', '</entity_text></entity>', 1)
        d = parse_tt_record(
            source.encode(), source_record_id="fixture/fixture:entity",
            source_path="fixture/fixture_TT/entity.tt",
            upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN,
        )
        self.assertIsNone(d.entities[0].source_text_literal)
        self.assertEqual(len(d.entity_source_annotations), 1)
        self.assertEqual(d.entity_source_annotations[0].kind, "entity_text")

    def test_original_source_parity_is_part_of_exact_full_build_gate(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "tests/live_issue187_entity_source_parity.py").read_text(
            encoding="utf-8"
        )
        workflow = (root / ".github/workflows/issue69-full-verse-census.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("cpr.31.14.tt", script)
        self.assertIn("source_attr_entity_text", script)
        self.assertIn("source_sha256", script)
        self.assertIn("live_issue187_entity_source_parity.py pinned-coptic", workflow)
        self.assertIn("--native", workflow)
        self.assertNotIn("print(source)", script)


if __name__ == "__main__":
    unittest.main()
