"""RED-first contract for the pinned full-source TT tag matrix (#118).

The raw census is an immutable, independently run GitHub Actions artifact;
this test checks the checked-in human-reviewable transcription and taxonomy.
It does not claim source annotations have all been modeled in native TF.
"""
from __future__ import annotations

import csv
from pathlib import Path
import unittest

MATRIX = Path(__file__).resolve().parents[1] / "research/issue-118/tag_matrix.csv"


class SourceTagMatrixTests(unittest.TestCase):
    def test_complete_observed_tag_inventory_and_source_counts(self):
        with MATRIX.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 101)
        self.assertEqual(len({row["tag"] for row in rows}), 101)
        self.assertEqual(sum(int(row["source_occurrences"]) for row in rows), 6_621_410)
        self.assertEqual(
            {key: sum(row["baseline_status"] == key for row in rows)
             for key in ("modeled", "unknown_unmodeled", "requires_modeling")},
            {"modeled": 18, "unknown_unmodeled": 82, "requires_modeling": 1},
        )
        by_tag = {row["tag"]: row for row in rows}
        for tag, count in [("lang", 110_148), ("morph", 78_265),
                           ("note", 2_822), ("norm", 2_394_354)]:
            self.assertEqual(int(by_tag[tag]["source_occurrences"]), count)
        for row in rows:
            total = int(row["source_occurrences"])
            self.assertGreater(total, 0, row["tag"])
            self.assertGreater(int(row["source_collections"]), 0, row["tag"])
            self.assertLessEqual(int(row["source_collections"]), 78, row["tag"])
            self.assertLessEqual(int(row["inside_norm_openings"]), total, row["tag"])
            self.assertLessEqual(int(row["present_empty_attributes"]), total, row["tag"])
            self.assertIn(row["baseline_status"],
                          {"modeled", "unknown_unmodeled", "requires_modeling"})
            self.assertIn(row["provisional_family"],
                          {"linguistic", "grouping", "editorial", "alternate_reference",
                           "entity", "structure", "other"})


if __name__ == "__main__":
    unittest.main()
