"""RED-first batch evidence for pinned Coptic OT source verse-zero markers.

Do not invent LXX verse zero, Psalm superscriptions, or biblical text from
syntactic TT zero literals. Group only already-collected source-event evidence.
"""
from __future__ import annotations

import unittest
from copticscriptorium_tf.ot_verse_anomalies import CopticOtVerseAnomalyBatch

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
HASH_A = "a" * 64
HASH_B = "b" * 64
PSALM = (
    '<meta chapter="1">'
    '<verse_n verse_n="0"><norm norm="p">p</norm>'
    '<verse_n verse_n="1"><norm norm="q">q</norm>'
    '<verse_n verse_n="00"><norm norm="r">r</norm>'
    '<chapter_n chapter_n="2">'
    '<verse_n verse_n="0"><norm norm="s">s</norm>'
)
EXODUS = (
    '<meta chapter="25">'
    '<verse_n verse_n="000"><norm norm="e">e</norm>'
)
NON_OT = (
    '<meta chapter="1">'
    '<verse_n verse_n="0"><norm norm="n">n</norm>'
)


def scan(batch: CopticOtVerseAnomalyBatch, *, reverse: bool = False) -> None:
    specs = (
        (PSALM, "sahidic.ot/sahidic.ot:19_Psalmi_001", HASH_A, "ot_candidate",
         "sahidic.ot", "ot.ps", "1", "coptot_ed", "Ps"),
        (EXODUS, "bohairic.ot/bohairic.ot:02_Exodus_25", HASH_B, "ot_candidate",
         "bohairic.ot", "ot.exod", "25", "bohairic_ed", "Exod"),
        (NON_OT, "sahidica.nt/sahidica.nt:41_Mark_01", "c"*64, "nt_candidate",
         "sahidica.nt", "nt.mark", "1", "sahidica_nt", None),
    )
    for args in (reversed(specs) if reverse else specs):
        raw, record_id, sha, scope, corpus, cts, chapter, edition, book = args
        batch.add(
            raw, record_id, source_sha256=sha, scope=scope, corpus=corpus,
            cts_work=cts, chapter=chapter, edition=edition, lxx_book=book,
        )


class SourceVerseZeroGroupingTests(unittest.TestCase):
    def test_preserves_same_record_distinct_chapters_and_all_exact_positions(self):
        batch = CopticOtVerseAnomalyBatch(source_commit=PIN)
        scan(batch)
        report = batch.report()
        groups = report["zero_literal_source_groups"]
        self.assertEqual(len(groups), 3)
        self.assertEqual(sum(g["marker_count"] for g in groups), 4)
        by_key = {(g["source_record_id"], g["source_chapter"]): g for g in groups}
        p1 = by_key[("sahidic.ot/sahidic.ot:19_Psalmi_001", "1")]
        p2 = by_key[("sahidic.ot/sahidic.ot:19_Psalmi_001", "2")]
        ex = by_key[("bohairic.ot/bohairic.ot:02_Exodus_25", "25")]
        self.assertEqual(p1["marker_count"], 2)
        self.assertEqual([m["literal"] for m in p1["markers"]], ["0", "00"])
        self.assertEqual([m["source_marker_ordinal"] for m in p1["markers"]], [1, 3])
        self.assertEqual(
            [m["source_tag_offset"] for m in p1["markers"]],
            [PSALM.index('<verse_n verse_n="0">'), PSALM.index('<verse_n verse_n="00">')],
        )
        self.assertEqual([m["source_word_starts_before"] for m in p1["markers"]], [0, 2])
        self.assertEqual(p1["source_sha256"], HASH_A)
        self.assertEqual(p1["source_cts_work"], "ot.ps")
        self.assertEqual(p1["source_edition"], "coptot_ed")
        self.assertEqual(p2["marker_count"], 1)
        self.assertEqual(p2["markers"][0]["literal"], "0")
        self.assertEqual(ex["source_cts_work"], "ot.exod")
        self.assertEqual(ex["markers"][0]["literal"], "000")
        self.assertEqual(ex["source_sha256"], HASH_B)
        self.assertNotIn("sahidica.nt/sahidica.nt:41_Mark_01",
                         [g["source_record_id"] for g in groups])
        self.assertEqual(report["zero_literal_work_edition_counts"],
                         {"ot.exod|bohairic_ed": 1, "ot.ps|coptot_ed": 3})
        self.assertEqual(report["zero_literal_source_record_count"], 2)
        self.assertEqual(report["invalid_literal_classes"]["zero_literal"], 4)

    def test_deterministic_under_reverse_input_order_and_no_greek_zero_lookup(self):
        a = CopticOtVerseAnomalyBatch(source_commit=PIN)
        b = CopticOtVerseAnomalyBatch(source_commit=PIN)
        scan(a)
        scan(b, reverse=True)
        called = []
        def forbidden_lookup(*args):
            called.append(args)
            raise AssertionError("a source zero must not be probed as a Greek verse")
        for batch in (a, b):
            batch.inspect_greek(
                verse_lookup=forbidden_lookup,
                subverse_lookup=lambda node: (),
            )
        self.assertEqual(called, [])
        self.assertEqual(a.report()["zero_literal_source_groups"],
                         b.report()["zero_literal_source_groups"])
        self.assertTrue(all(
            m["literal"].isdigit()
            for g in a.report()["zero_literal_source_groups"]
            for m in g["markers"]
        ))
        self.assertEqual(
            {c["greek_status"] for c in a.report()["cases"]},
            {"not_inferable"},
        )


if __name__ == "__main__":
    unittest.main()
