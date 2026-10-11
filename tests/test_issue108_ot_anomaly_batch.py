"""RED-first #108 exact source marker anomalies vs Greek reference addresses."""
from __future__ import annotations

import unittest

from copticscriptorium_tf.ot_verse_anomalies import CopticOtVerseAnomalyBatch

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
H = "a" * 64


class SourceAnomalyBatchTests(unittest.TestCase):
    def make(self, *, scope="ot_candidate"):
        batch = CopticOtVerseAnomalyBatch(source_commit=PIN)
        return batch, scope

    def test_gaps_and_invalid_literals_have_exact_distinct_source_events(self):
        batch, scope = self.make()
        text = (
            '<meta chapter="2" document_cts_urn="urn:cts:copticLit:ot.ruth.coptot_ed:2">'
            '<verse_n verse_n="1"><norm norm="x">x</norm>'
            '<verse_n verse_n="4"><norm norm="y">y</norm>'
            '<verse_n verse_n="0"><norm norm="z">z</norm>'
            '<verse_n verse_n=""><norm norm="u">u</norm>'
            '<verse_n><norm norm="v">v</norm>'
        )
        batch.add(text, "sahidic.ruth/sahidic.ruth:Ruth_02", source_sha256=H,
                  scope=scope, corpus="sahidic.ruth",
                  cts_work="ot.ruth", chapter="2", edition="coptot_ed")
        rows = batch.report()["cases"]
        self.assertEqual([r["kind"] for r in rows], [
            "gapped", "missing_or_nonpositive_literal",
            "missing_or_nonpositive_literal", "missing_or_nonpositive_literal"
        ])
        self.assertEqual(rows[0]["previous_verse"], 1)
        self.assertEqual(rows[0]["current_verse"], 4)
        self.assertEqual(rows[0]["missing_verse_numbers"], [2, 3])
        self.assertEqual(rows[0]["source_word_starts_before"], 1)
        self.assertEqual(rows[0]["source_marker_ordinal"], 2)
        self.assertEqual(rows[0]["source_tag_offset"], text.index('<verse_n verse_n="4">'))
        self.assertEqual(rows[0]["source_sha256"], H)
        self.assertEqual([r["literal"] for r in rows[1:]], ["0", "", None])
        self.assertEqual(batch.report()["counts"], {
            "gapped": 1, "missing_or_nonpositive_literal": 3
        })

    def test_chapter_resets_and_non_ot_are_excluded(self):
        batch, _ = self.make()
        batch.add(
            '<verse_n verse_n="8"><norm norm="a">a</norm>'
            '<chapter_n chapter_n="2"><verse_n verse_n="1"><norm norm="b">b</norm>',
            "sahidic.ruth/ruth:one", source_sha256=H,
            scope="ot_candidate", corpus="sahidic.ruth",
            cts_work="ot.ruth", chapter="1", edition="example",
        )
        batch.add('<verse_n verse_n="2"><verse_n verse_n="5">',
                  "ap/ap:two", source_sha256=H, scope="nt_candidate",
                  corpus="ap", cts_work="nt.mark", chapter="1", edition="example")
        self.assertEqual(batch.report()["cases"], [])
        self.assertEqual(batch.report()["counts"], {})
        self.assertEqual(batch.report()["scanned_ot_records"], 1)

    def test_lxx_crosscheck_reports_only_existing_missing_address_not_equivalence(self):
        batch, _ = self.make()
        text = '<verse_n verse_n="1"><verse_n verse_n="4">'
        batch.add(text, "sahidic.ruth/ruth:one", source_sha256=H,
                  scope="ot_candidate", corpus="sahidic.ruth",
                  cts_work="ot.ruth", chapter="2", edition="example",
                  lxx_book="Ruth")
        calls = []
        batch.inspect_greek(
            verse_lookup=lambda b, c, v: calls.append((b, c, v)) or ({2: 200, 3: None}[v]),
            subverse_lookup=lambda node: ("a", "b") if node == 200 else (),
        )
        row = batch.report()["cases"][0]
        self.assertEqual(calls, [("Ruth", 2, 2), ("Ruth", 2, 3)])
        self.assertEqual(row["greek_missing_intermediate"], [
            {"verse": 2, "address": "present", "subverse_count": 2},
            {"verse": 3, "address": "absent", "subverse_count": 0},
        ])
        self.assertEqual(row["interpretation"], "Greek reference existence only, not textual equivalence")

    def test_invalid_source_pin_and_unreviewed_greek_book_are_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "source commit"):
            CopticOtVerseAnomalyBatch(source_commit="moving")
        batch, _ = self.make()
        batch.add(
            '<verse_n verse_n="1"><verse_n verse_n="4">',
            "sahidic.ruth/ruth:one", source_sha256=H, scope="ot_candidate",
            corpus="sahidic.ruth", cts_work="ot.ruth", chapter="2", edition="example",
        )
        batch.inspect_greek(
            verse_lookup=lambda *args: self.fail("must not map absent reviewed book"),
            subverse_lookup=lambda node: (),
        )
        self.assertEqual(batch.report()["cases"][0]["greek_missing_intermediate"], [])
        self.assertEqual(batch.report()["cases"][0]["greek_status"], "source_reference_unclassified")


if __name__ == "__main__":
    unittest.main()
