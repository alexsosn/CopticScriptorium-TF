"""RED contracts for full pinned Coptic biblical metadata coverage inventory.

A book-like title, any verse marker, or a filename must not become a
verified Greek/Coptic alignment. Only conservative source-family/CTS evidence
is classified; conflicting/unknown records remain visible in the audit.
"""
from __future__ import annotations

import unittest

from copticscriptorium_tf.ot_inventory import classify_biblical_record


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


if __name__ == "__main__":
    unittest.main()
