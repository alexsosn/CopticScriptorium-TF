"""RED-first: Greek *edition alternative* address probes, not alignment (#149)."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import unittest

from copticscriptorium_tf.ot_variant_probe import (
    EditionProbeError,
    GREEK_VARIANTS,
    probe_pinned_variant_gaps,
)

FIXTURE = Path(__file__).resolve().parents[1] / "research/issue-149/pinned-ambiguous-gaps.json"


class PinnedAlternativeGreekEditionTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_full_real_source_report_fixture_has_ten_events_seven_records_and_fifty_skips(self):
        calls = []
        def lookup(book, chapter, verse):
            calls.append((book, chapter, verse))
            return 1000 + verse if book in {"Dan", "TobBA", "Sus", "Bel"} else None

        rows = probe_pinned_variant_gaps(self.data, lookup=lookup)
        self.assertEqual(len(rows), 10)
        self.assertEqual(len({r.source_record_id for r in rows}), 7)
        self.assertEqual(
            sum(r.current_verse - r.previous_verse - 1 for r in rows), 50
        )
        self.assertEqual(
            Counter(r.source_cts_work for r in rows),
            {"ot.dan": 6, "ot.tob": 2, "ot.sus": 1, "ot.bel": 1},
        )
        for row in rows:
            self.assertEqual(row.status, "unresolved_edition")
            self.assertIsNone(row.selected_lxx_book)
            self.assertEqual(len(row.variants), 2)
            for variant in row.variants:
                self.assertIn(variant.book, GREEK_VARIANTS[row.source_cts_work])
                self.assertEqual(
                    len(variant.intermediate),
                    row.current_verse - row.previous_verse - 1,
                )
        self.assertTrue(any(v.node is None for r in rows for x in r.variants
                            for v in x.intermediate))
        self.assertIn(("DanTh", 4, 13), calls)
        self.assertIn(("Dan", 4, 13), calls)
        self.assertIn(("TobBA", 5, 10), calls)
        self.assertIn(("TobS", 5, 10), calls)

    def test_matching_one_greek_book_only_never_certifies_source_edition(self):
        rows = probe_pinned_variant_gaps(
            self.data,
            lookup=lambda book, chapter, verse: 12 if book.endswith("Th") else None,
        )
        self.assertEqual({row.status for row in rows}, {"unresolved_edition"})
        self.assertTrue(all(row.selected_lxx_book is None for row in rows))

    def test_malformed_source_provenance_and_duplicate_marker_fail_closed(self):
        for mutate in (
            lambda d: d.update(coptic_source_commit="0" * 40),
            lambda d: d["records"][0].update(source_sha256="x" * 64),
            lambda d: d["records"][0]["events"][0].update(current_verse=13),
            lambda d: d["records"][0]["events"].append(
                deepcopy(d["records"][0]["events"][0])
            ),
            lambda d: d["records"][0].update(source_cts_work="ot.mark"),
            lambda d: d["records"][0].update(source_edition="unknown"),
            # Same number of skipped verses, but forged source event placement.
            lambda d: d["records"][0]["events"][0].update(
                previous_verse=11, current_verse=16,
            ),
            lambda d: d["records"][0]["events"][0].update(
                source_marker_ordinal=5,
            ),
        ):
            data = deepcopy(self.data)
            mutate(data)
            with self.subTest(mutator=str(mutate)):
                with self.assertRaises(EditionProbeError):
                    probe_pinned_variant_gaps(data, lookup=lambda *args: 2)

    def test_nonpositive_greek_node_and_noninteger_subverse_count_fail_closed(self):
        with self.assertRaises(EditionProbeError):
            probe_pinned_variant_gaps(self.data, lookup=lambda *args: True)
        with self.assertRaises(EditionProbeError):
            probe_pinned_variant_gaps(
                self.data, lookup=lambda *args: 9,
                subverse_count=lambda node: -1,
            )

    def test_deterministic_reports_independent_of_record_event_input_order(self):
        a = probe_pinned_variant_gaps(self.data, lookup=lambda b, c, v: v)
        swapped = deepcopy(self.data)
        swapped["records"].reverse()
        swapped["records"][1]["events"].reverse()
        b = probe_pinned_variant_gaps(swapped, lookup=lambda b, c, v: v)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
