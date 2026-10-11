"""RED-first: comprehensive noncandidate source-shape census without corpus text."""
from dataclasses import replace
from unittest import TestCase

from copticscriptorium_tf.nt_reference import CopticSblReference
from copticscriptorium_tf.nt_source_diagnostics import NonCandidateInventory

MARK = "sahidica.mark/sahidica.mark:Mark_01"
TREE = "coptic-treebank/coptic.treebank:Mark_01"


def ref(*, status="ambiguous", record=MARK, ordinal=1, kind="sbl_greek",
        reason="missing or malformed source NT reference evidence",
        vid="urn:cts:copticLit:nt.mark.sahidica_ed:1.1", editor=None,
        ordinals=(1,)):
    return CopticSblReference(
        source_record_id=record, source_ordinal=ordinal, source_kind=kind,
        source_word_ordinals=ordinals, source_verse_n="1",
        source_vid_n=vid, source_verse_vid=editor,
        target_book="Mark", target_chapter=1, target_verse=1,
        target_node=None, shared_id=None, status=status,
        evidence="source", reason=reason,
    )


class NoncandidateInventoryTests(TestCase):
    def test_reports_every_source_ordinal_without_original_text(self):
        inventory = NonCandidateInventory()
        inventory.add(MARK, [("sbl_greek", "41N 1:5"),
                             ("sbl_apparatus", "⸂Λόγος⸃ • WH Treg")],
                      [ref(vid="ἐν ἀρχῇ",editor=None),
                       ref(kind="sbl_apparatus",ordinal=2,vid=None)])
        report = inventory.finish(expected_statuses={"ambiguous": 2},
                                  expected_annotated=1, expected_total=2)
        self.assertEqual(report["source_annotations"], 2)
        self.assertEqual(report["noncandidate_occurrences"], 2)
        self.assertEqual(len(report["inventory"]), 2)
        self.assertEqual(report["by_physical_record"][MARK]["ambiguous"], 2)
        self.assertEqual(report["inventory"][0]["vid_n_shape"], "other")
        self.assertEqual(report["inventory"][0]["verse_vid_shape"], "missing")
        self.assertEqual(report["inventory"][0]["sbl_value_shape"], "editor_reference")
        text = str(report)
        for original in ["41N 1:5", "ἐν ἀρχῇ", "Λόγος", "WH Treg"]:
            self.assertNotIn(original, text)
        self.assertIn("missing_nt_reference_evidence", text)

    def test_treebank_copy_retains_distinct_source_identity(self):
        inventory = NonCandidateInventory()
        for record in (MARK, TREE):
            inventory.add(record,[("sbl_greek","41N 1:5")],[ref(record=record)])
        report=inventory.finish(expected_statuses={"ambiguous":2},
                                expected_annotated=2,expected_total=2)
        self.assertEqual(len(report["by_physical_record"]),2)
        self.assertEqual(len(report["inventory"]),2)

    def test_duplicate_physical_record_is_rejected(self):
        inventory = NonCandidateInventory()
        inventory.add(MARK,[("sbl_greek","x")],[ref()])
        with self.assertRaisesRegex(ValueError,"duplicate"):
            inventory.add(MARK,[("sbl_greek","x")],[ref()])

    def test_duplicate_or_missing_source_occurrence_is_rejected(self):
        cases = ([], [ref(ordinal=2)], [ref(kind="sbl_apparatus")],
                 [ref(), ref(ordinal=2)])
        for refs in cases:
            with self.subTest(refs=refs):
                inventory = NonCandidateInventory()
                with self.assertRaisesRegex(ValueError,"occurrence"):
                    inventory.add(MARK,[("sbl_greek","x")],refs)

    def test_unknown_status_or_unknown_reason_fails_closed(self):
        for bad in (ref(status="bad"),
                    ref(reason="raw Greek text accidentally copied"),
                    ref(status="unresolved",reason="some new text")):
            with self.subTest(status=bad.status,reason=bad.reason):
                inventory=NonCandidateInventory()
                with self.assertRaisesRegex(ValueError,"reason|status"):
                    inventory.add(MARK,[("sbl_greek","x")],[bad])

    def test_candidate_is_counted_but_never_added_to_inventory(self):
        a=ref(status="reference_candidate",
              reason="matching edition-qualified verse address; textual equivalence unverified")
        a=replace(a,target_node=201,shared_id="morphgnt/sblgnt:6.12:Mark:1:1")
        inventory=NonCandidateInventory()
        inventory.add(MARK,[("sbl_greek","x")],[a])
        result=inventory.finish(expected_statuses={"reference_candidate":1},
                                expected_annotated=1,expected_total=1)
        self.assertEqual(result["inventory"],[])
        self.assertEqual(result["noncandidate_occurrences"],0)

    def test_pinned_count_drift_and_extra_status_fail(self):
        inventory=NonCandidateInventory()
        inventory.add(MARK,[("sbl_greek","x")],[ref()])
        for expected,docs,total in [
            ({"ambiguous":437,"unresolved":9},1,1),
            ({"ambiguous":1},2,1),
            ({"ambiguous":1},1,2747),
            ({"ambiguous":1,"unresolved":0},1,1),
        ]:
            with self.subTest(expected=expected,docs=docs,total=total):
                with self.assertRaisesRegex(ValueError,"count"):
                    inventory.finish(expected_statuses=expected,
                                     expected_annotated=docs,expected_total=total)

    def test_no_word_locus_and_malformed_editor_are_explicit_shapes(self):
        inventory=NonCandidateInventory()
        case=ref(status="unresolved",ordinals=(),vid="46N 1:1",
                 editor="arbitrary Greek",reason="SBL occurrence has no fully enclosed Coptic word span")
        inventory.add(MARK,[("sbl_greek","β")],[case])
        report=inventory.finish(expected_statuses={"unresolved":1},
                                expected_annotated=1,expected_total=1)
        row,=report["inventory"]
        self.assertEqual(row["word_locus"], "no_complete_word")
        self.assertEqual(row["vid_n_shape"],"editor_reference")
        self.assertEqual(row["verse_vid_shape"],"other")
        self.assertEqual(row["reason_code"],"no_complete_coptic_word_span")
