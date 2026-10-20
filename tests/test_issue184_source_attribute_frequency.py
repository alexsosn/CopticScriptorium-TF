"""#184 RED-first: source-key occurrence census, independent of TF parser."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/live_issue110_wrapper_census.py"


class SourceAttributeFrequencyTests(unittest.TestCase):
    def test_dual_morph_attributes_are_counted_per_original_opening(self):
        census = runpy.run_path(str(SOURCE))
        openings = Counter()
        inside = Counter()
        attributes = Counter()
        collection = Counter()
        examples = {}
        empty = Counter()
        duplicates = Counter()
        watched = {}
        raw = (
            '<meta corpus="fixture">'
            '<norm_group norm_group="sample">'
            '<norm norm="AB">'
            '<morph morph="a" lang="Greek">a</morph>'
            '<morph morph="b">b</morph>'
            '</norm></norm_group>'
        ).encode("utf-8")
        n = census["audit_tt"](
            raw, "fixture/fixture_TT/one.tt", openings, inside,
            attributes, collection, examples, empty, duplicates,
            watched_examples=watched,
        )
        self.assertEqual(n, 5)
        self.assertEqual(attributes["morph", "morph"], 2)
        self.assertEqual(attributes["morph", "lang"], 1)
        self.assertEqual(watched[("morph", "lang")], ["fixture/fixture_TT/one.tt"])

    def test_attribute_census_is_explicitly_source_only(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"source_attribute_pair_counts"', source)
        self.assertIn('"morph_lang_source_records"', source)
        self.assertIn('"scope": "raw source inventory only', source)
        self.assertNotIn("print(raw)", source)
        self.assertNotIn("print(text)", source)


if __name__ == "__main__":
    unittest.main()
