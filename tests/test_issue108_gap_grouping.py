"""RED-first: retain all source-edition gap evidence as auditable batches (#108).

An LXX address existing within a Coptic source-number gap is not proof of
omitted Coptic text or textual correspondence.
"""
from __future__ import annotations

import unittest
from copticscriptorium_tf.ot_verse_anomalies import CopticOtVerseAnomalyBatch

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
HASH_A, HASH_B = "a" * 64, "b" * 64
RUTH = (
    '<meta chapter="2">'
    '<verse_n verse_n="1"><norm norm="a">a</norm>'
    '<verse_n verse_n="4"><norm norm="b">b</norm>'
    '<verse_n verse_n="6"><norm norm="c">c</norm>'
    '<chapter_n chapter_n="3">'
    '<verse_n verse_n="1"><norm norm="d">d</norm>'
    '<verse_n verse_n="3"><norm norm="e">e</norm>'
)
EXODUS = (
    '<meta chapter="25">'
    '<verse_n verse_n="10"><norm norm="a">a</norm>'
    '<verse_n verse_n="12"><norm norm="b">b</norm>'
)
NON_OT = (
    '<meta chapter="1">'
    '<verse_n verse_n="1"><norm norm="n">n</norm>'
    '<verse_n verse_n="20"><norm norm="m">m</norm>'
)


def scan(*, reverse: bool = False) -> CopticOtVerseAnomalyBatch:
    a = CopticOtVerseAnomalyBatch(source_commit=PIN)
    cases = (
        (RUTH, "sahidic.ruth/sahidic.ruth:Ruth_02", HASH_A,
         "ot_candidate", "sahidic.ruth", "ot.ruth", "2", "coptot_ed", "Ruth"),
        (EXODUS, "bohairic.ot/bohairic.ot:02_Exodus_25", HASH_B,
         "ot_candidate", "bohairic.ot", "ot.exod", "25", "bohairic_ed", None),
        (NON_OT, "sahidica.nt/sahidica.nt:41_Mark_01", "c"*64,
         "nt_candidate", "sahidica.nt", "nt.mark", "1", "sahidica_nt", None),
    )
    for raw, source_id, sha, scope, corpus, cts, chapter, edition, book in (
        reversed(cases) if reverse else cases
    ):
        a.add(raw, source_id, source_sha256=sha, scope=scope,
              corpus=corpus, cts_work=cts, chapter=chapter, edition=edition,
              lxx_book=book)
    return a


class GappedOtMarkerBatchTests(unittest.TestCase):
    def test_lossless_source_groups_span_multiple_chapters_and_witnesses(self):
        audit = scan()
        report = audit.report()
        groups = report["gapped_source_groups"]
        self.assertEqual(report["counts"]["gapped"], 4)
        self.assertEqual(len(groups), 3)
        self.assertEqual(sum(g["marker_count"] for g in groups), 4)
        by_key = {(g["source_record_id"], g["source_chapter"]): g for g in groups}
        second = by_key[("sahidic.ruth/sahidic.ruth:Ruth_02", "2")]
        self.assertEqual(second["source_sha256"], HASH_A)
        self.assertEqual(second["source_cts_work"], "ot.ruth")
        self.assertEqual(second["source_edition"], "coptot_ed")
        self.assertEqual(second["lxx_book"], "Ruth")
        self.assertEqual(second["marker_count"], 2)
        self.assertEqual([(m["previous_verse"], m["current_verse"],
                           m["missing_verse_numbers"]) for m in second["markers"]],
                         [(1, 4, [2, 3]), (4, 6, [5])])
        self.assertEqual([m["source_marker_ordinal"] for m in second["markers"]], [2, 3])
        self.assertEqual([m["source_word_starts_before"] for m in second["markers"]], [1, 2])
        self.assertEqual(
            second["markers"][0]["source_tag_offset"],
            RUTH.index('<verse_n verse_n="4">'),
        )
        self.assertEqual(by_key[("sahidic.ruth/sahidic.ruth:Ruth_02", "3")]["marker_count"], 1)
        self.assertEqual(report["gapped_source_record_count"], 2)
        self.assertEqual(
            report["gapped_work_edition_counts"],
            {"ot.exod|bohairic_ed": 1, "ot.ruth|coptot_ed": 3},
        )
        self.assertNotIn("sahidica.nt/sahidica.nt:41_Mark_01",
                         [g["source_record_id"] for g in groups])

    def test_greek_address_evidence_is_event_local_and_not_text_alignment(self):
        audit = scan()
        queried = []
        def verse_lookup(book, chapter, verse):
            queried.append((book, chapter, verse))
            if (book, chapter, verse) in {
                ("Ruth", 2, 2), ("Ruth", 2, 5), ("Ruth", 3, 2)
            }:
                return 1000 + verse
            return None
        audit.inspect_greek(
            verse_lookup=verse_lookup,
            subverse_lookup=lambda node: ("A", "B") if node == 1002 else (),
        )
        report = audit.report()
        self.assertEqual(set(queried), {
            ("Ruth", 2, 2), ("Ruth", 2, 3), ("Ruth", 2, 5),
            ("Ruth", 3, 2),
        })
        self.assertEqual(
            report["gapped_intermediate_address_status_counts"],
            {"present": 3, "absent": 1},
        )
        self.assertEqual(
            report["gapped_greek_check_status_counts"],
            {"crosschecked_address_only": 3, "source_reference_unclassified": 1},
        )
        root = next(g for g in report["gapped_source_groups"]
                    if g["source_record_id"].startswith("sahidic.ruth") and
                    g["source_chapter"] == "2")
        self.assertEqual(root["markers"][0]["greek_missing_intermediate"], [
            {"verse": 2, "address": "present", "subverse_count": 2},
            {"verse": 3, "address": "absent", "subverse_count": 0},
        ])
        self.assertIn("not", root["interpretation"])
        unresolved = next(g for g in report["gapped_source_groups"]
                          if g["source_record_id"].startswith("bohairic.ot"))
        self.assertEqual(unresolved["markers"][0]["greek_status"],
                         "source_reference_unclassified")
        self.assertEqual(unresolved["markers"][0]["greek_missing_intermediate"], [])

    def test_reversed_ingestion_deterministic_and_not_checked_remains_explicit(self):
        normal, reversed_order = scan(), scan(reverse=True)
        self.assertEqual(normal.report()["gapped_source_groups"],
                         reversed_order.report()["gapped_source_groups"])
        report = normal.report()
        self.assertEqual(report["gapped_greek_check_status_counts"], {"not_checked": 4})
        self.assertEqual(report["gapped_intermediate_address_status_counts"], {})
        self.assertTrue(all(
            m["greek_missing_intermediate"] == []
            for g in report["gapped_source_groups"] for m in g["markers"]
        ))


if __name__ == "__main__":
    unittest.main()
