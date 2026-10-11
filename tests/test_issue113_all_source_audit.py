"""RED-first independent audit invariants for all SBL source occurrences."""
from dataclasses import replace
import unittest

from copticscriptorium_tf.nt_reference_audit import CandidateAudit
from copticscriptorium_tf.nt_reference import CopticSblReference, GREEK_NT_EDITION


def candidate(*, ordinal=1, kind="sbl_greek", record="sahidica.mark/sahidica.mark:Mark_02",
              status="reference_candidate", verse=1, target_node=42):
    present = status == "reference_candidate"
    return CopticSblReference(
        source_record_id=record, source_ordinal=ordinal, source_kind=kind,
        source_word_ordinals=(1, 2), source_verse_n=str(verse),
        source_vid_n=f"urn:cts:copticLit:nt.mark.sahidica_ed:2.{verse}",
        source_verse_vid=f"41N 2:{verse}", target_book="Mark",
        target_chapter=2, target_verse=verse, target_node=target_node if present else None,
        shared_id=f"{GREEK_NT_EDITION}:Mark:2:{verse}" if present else None,
        status=status, evidence="source marks", reason="test fixture",
    )


def matched_lookup(node):
    return ("Mark", 2, 1) if node == 42 else None


class AllSourceAuditTests(unittest.TestCase):
    def test_matching_annotation_is_preserved_and_reverse_section_verified(self):
        a = CandidateAudit()
        a.add("sahidica.mark/sahidica.mark:Mark_02", [("sbl_greek", "Greek source")],
              [candidate()], reverse_lookup=matched_lookup)
        a.add_unannotated("other/doc:empty")
        report = a.finish(expected_physical=2, expected_annotated=1,
                          expected_kinds={"sbl_greek": 1})
        self.assertEqual(report["statuses"]["reference_candidate"], 1)
        self.assertEqual(report["physical_records"], 2)
        self.assertEqual(report["annotated_records"], 1)
        self.assertNotIn("Greek source", str(report))

    def test_duplicate_physical_document_is_error(self):
        a = CandidateAudit()
        a.add("sahidica.mark/sahidica.mark:Mark_02",
              [("sbl_greek", "x")], [candidate()], reverse_lookup=matched_lookup)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            a.add("sahidica.mark/sahidica.mark:Mark_02",
                  [("sbl_greek", "x")], [candidate()], reverse_lookup=matched_lookup)

    def test_changed_kind_or_ordinal_is_error(self):
        for changed in (candidate(kind="sbl_apparatus"), candidate(ordinal=2)):
            a = CandidateAudit()
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "occurrence"):
                a.add(changed.source_record_id, [("sbl_greek", "x")],
                      [changed], reverse_lookup=matched_lookup)

    def test_extra_and_missing_occurrences_are_errors(self):
        for refs in ([], [candidate(), candidate(ordinal=2)]):
            a = CandidateAudit()
            with self.subTest(count=len(refs)), self.assertRaisesRegex(ValueError, "occurrence"):
                a.add("sahidica.mark/sahidica.mark:Mark_02",
                      [("sbl_greek", "x")], refs, reverse_lookup=matched_lookup)

    def test_misrepresented_parent_verse_is_error(self):
        a = CandidateAudit()
        with self.assertRaisesRegex(ValueError, "reverse"):
            a.add("sahidica.mark/sahidica.mark:Mark_02", [("sbl_greek", "x")],
                  [candidate()], reverse_lookup=lambda node: ("Mark", 2, 2))

    def test_wrong_edition_ref_is_error(self):
        a = CandidateAudit()
        with self.assertRaisesRegex(ValueError, "edition"):
            a.add("sahidica.mark/sahidica.mark:Mark_02", [("sbl_greek", "x")],
                  [replace(candidate(), shared_id="wrong")],
                  reverse_lookup=matched_lookup)

    def test_unresolved_never_fabricates_target(self):
        a = CandidateAudit()
        with self.assertRaisesRegex(ValueError, "foreign"):
            a.add("sahidica.mark/sahidica.mark:Mark_02", [("sbl_greek", "x")],
                  [replace(candidate(status="unresolved"), target_node=42)],
                  reverse_lookup=matched_lookup)

    def test_unreviewed_occurrence_remains_in_coverage(self):
        a = CandidateAudit()
        a.add("sahidica.mark/sahidica.mark:Mark_02", [("sbl_greek", "x")],
              [candidate(status="ambiguous")], reverse_lookup=matched_lookup)
        r = a.finish(expected_physical=1, expected_annotated=1,
                     expected_kinds={"sbl_greek": 1})
        self.assertEqual(r["statuses"]["ambiguous"], 1)

    def test_source_count_drift_is_fail_closed(self):
        a = CandidateAudit()
        a.add_unannotated("empty/docs:0")
        with self.assertRaisesRegex(ValueError, "count"):
            a.finish(expected_physical=2628, expected_annotated=48,
                     expected_kinds={"sbl_greek": 1652, "sbl_apparatus": 1095})

    def test_source_name_and_literal_never_escape_report(self):
        a = CandidateAudit()
        a.add("sahidica.mark/sahidica.mark:Mark_02", [("sbl_greek", "⸀λόγος· ")],
              [candidate()], reverse_lookup=matched_lookup)
        report = a.finish(expected_physical=1, expected_annotated=1,
                          expected_kinds={"sbl_greek": 1})
        self.assertNotIn("λόγος", str(report))
        self.assertNotIn("⸀λόγος· ", str(report))
        self.assertIn("source_annotation_kinds", report)


if __name__ == "__main__":
    unittest.main()
