"""RED/green tests for the pinned Zechariah primary-source diagnostic.

A numeric chapter shift is not proof of passage identity; the tests ensure
scope and no silently published/guessed crosswalk.
"""
from __future__ import annotations

from pathlib import Path
import unittest

from tests.live_issue95_zechariah import (
    COPTIC_PIN, LXX_PIN, OT_ZIPS, focused_verse, is_zechariah_source,
)


class ZechariahBoundaryAuditContracts(unittest.TestCase):
    def test_accept_exact_ot_cts_works_not_filename_or_non_ot_data(self):
        self.assertTrue(is_zechariah_source(
            b'<meta document_cts_urn="urn:cts:copticLit:ot.zach.coptot_ed:1" chapter="1">'
        ))
        self.assertTrue(is_zechariah_source(
            b'<meta document_cts_urn="urn:cts:copticLit:ot.zech.bohairic_ed:2" chapter="2">'
        ))
        for raw in (
            b'<meta title="Zechariah" chapter="1">',
            b'<meta document_cts_urn="urn:cts:copticLit:nt.zach.ed:1">',
            b'<meta document_cts_urn="urn:cts:copticLit:ot.zachariah.ed:1">',
            b'<meta document_cts_urn="urn:cts:copticLit:ot.zach.ed:1x">',
        ):
            with self.subTest(raw=raw):
                self.assertFalse(is_zechariah_source(raw))

    def test_window_is_bounded_to_chapter_transition(self):
        self.assertTrue(focused_verse(1, 18))
        self.assertTrue(focused_verse(1, 21))
        self.assertTrue(focused_verse(2, 1))
        self.assertTrue(focused_verse(2, 6))
        for c, v in ((1, 14), (1, 22), (2, 7), (3, 1), (None, 18), (1, None)):
            with self.subTest(chapter=c, verse=v):
                self.assertFalse(focused_verse(c, v))

    def test_pins_and_no_hidden_remapping_in_diagnostic(self):
        self.assertEqual(COPTIC_PIN, "3ac067f1709a0012daf39ea8da2fac79980176a5")
        self.assertEqual(LXX_PIN, "f32a98eddf7eb239aa73ab863d70381e416d5076")
        self.assertEqual(
            OT_ZIPS,
            ("sahidic.ot/sahidic.ot_TT.zip", "bohairic.ot/bohairic.ot_TT.zip"),
        )
        script = Path(__file__).with_name("live_issue95_zechariah.py").read_text()
        self.assertIn("hypothetical_shifted_greek", script)
        self.assertIn("diagnostic_only_not_textual_alignment", script)
        self.assertIn("verify_lxx_parent_feature_blobs", script)
        self.assertNotIn("write_reference_modules(", script)


if __name__ == "__main__":
    unittest.main()
