"""RED contracts for full pinned Coptic biblical metadata coverage inventory.

A book-like title, any verse marker, or a filename must not become a
verified Greek/Coptic alignment. Only conservative source-family/CTS evidence
is classified; conflicting/unknown records remain visible in the audit.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import unittest

from copticscriptorium_tf.ot_inventory import classify_biblical_record
from tests.live_issue75_ot_inventory import inventory_source_tree


class CopticOtInventoryEvidenceTests(unittest.TestCase):
    def test_known_ot_corpus_with_matching_ot_cts_is_only_candidate(self):
        result = classify_biblical_record(
            "sahidic.ruth",
            {"document_cts_urn": "urn:cts:copticLit:ot.ruth.coptot_ed:2",
             "chapter": "2", "title": "Ruth Chapter 2"},
        )
        self.assertEqual(result.status, "ot_candidate")
        self.assertEqual(result.cts_scope, "ot")
        self.assertEqual(result.cts_work, "ruth")
        self.assertIn("family:ot", result.evidence)
        self.assertIn("cts:ot", result.evidence)

    def test_plain_ot_family_without_cts_remains_provisional(self):
        result = classify_biblical_record("bohairic-habakkuk", {"chapter":"02"})
        self.assertEqual(result.status, "ot_candidate")
        self.assertIsNone(result.cts_scope)

    def test_known_nt_family_or_cts_never_auto_enters_ot(self):
        self.assertEqual(
            classify_biblical_record("sahidica.nt", {"chapter": "2"}).status,
            "nt_candidate",
        )
        self.assertEqual(
            classify_biblical_record(
                "unknown", {"document_cts_urn": "urn:cts:copticLit:nt.mark.ed:2"}
            ).status,
            "nt_candidate",
        )

    def test_nt_family_with_ot_cts_and_ot_family_with_nt_cts_are_conflicting(self):
        self.assertEqual(
            classify_biblical_record(
                "sahidica.nt", {"document_cts_urn":"urn:cts:copticLit:ot.ruth.ed:2"}
            ).status,
            "conflicting",
        )
        self.assertEqual(
            classify_biblical_record(
                "sahidic.ot", {"document_cts_urn":"urn:cts:copticLit:nt.mark.ed:2"}
            ).status,
            "conflicting",
        )

    def test_unknown_family_and_biblical_book_label_remain_undetermined(self):
        result = classify_biblical_record("bible", {"book": "Ruth", "chapter": "2"})
        self.assertEqual(result.status, "undetermined")
        self.assertEqual(result.book_literal, "Ruth")
        self.assertEqual(result.chapter_literal, "2")
        self.assertIsNone(result.cts_work)

    def test_cts_is_full_namespace_match_not_forged_substring(self):
        result = classify_biblical_record(
            "unknown", {"document_cts_urn": "urn:cts:unrelated:fake.ot.ruth.ed:2"}
        )
        self.assertEqual(result.status, "undetermined")
        self.assertIsNone(result.cts_work)
        result = classify_biblical_record(
            "unknown", {"document_cts_urn": "urn:cts:copticLit:ot.jonah.ed:2"}
        )
        self.assertEqual(result.status, "ot_candidate")
        self.assertEqual(result.cts_work, "jonah")

    def test_none_or_empty_metadata_is_not_biblical_assertion(self):
        result = classify_biblical_record("unknown", {})
        self.assertEqual(result.status, "undetermined")
        self.assertEqual(result.book_literal, "")
        self.assertEqual(result.chapter_literal, "")

    def test_real_source_tree_inventory_reads_direct_and_zip_tt_without_corpus_text(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            direct = root / "sahidic.ruth" / "sahidic.ruth_TT" / "Ruth_02.tt"
            direct.parent.mkdir(parents=True)
            direct.write_text(
                '<meta chapter="2" corpus="sahidic.ruth" '
                'document_cts_urn="urn:cts:copticLit:ot.ruth.ed:2">'
                '<verse_n verse_n="1">'
                '<norm_group norm_group="a"><norm xml:id="u1" '
                'new_sent="true" norm="SECRET_COPYRIGHTED_WORD">'
                'SECRET_COPYRIGHTED_WORD</norm></norm_group>',
                encoding="utf-8",
            )
            archive = root / "sahidica.nt" / "sahidica.nt_TT.zip"
            archive.parent.mkdir(parents=True)
            with ZipFile(archive, "w") as zipfile:
                zipfile.writestr(
                    "data/Mark_01.tt",
                    '<meta chapter="1" document_cts_urn="urn:cts:copticLit:nt.mark.ed:1">'
                    '<verse_n verse_n="1">'
                    '<norm_group norm_group="x"><norm new_sent="true" norm="SECRET_NT_TEXT">'
                    'SECRET_NT_TEXT</norm></norm_group>',
                )
            report = inventory_source_tree(
                root, expected_blobs=2, expected_records=2,
            )
            self.assertEqual(report["source_records"], 2)
            self.assertEqual(report["biblical_scope_counts"]["ot_candidate"], 1)
            self.assertEqual(report["biblical_scope_counts"]["nt_candidate"], 1)
            self.assertEqual(report["source_families"]["sahidic.ruth"]["verse_markers"], 1)
            self.assertEqual(report["source_families"]["sahidica.nt"]["verse_markers"], 1)
            self.assertNotIn("SECRET_COPYRIGHTED_WORD", repr(report))
            self.assertNotIn("SECRET_NT_TEXT", repr(report))


if __name__ == "__main__":
    unittest.main()
