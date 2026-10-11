"""RED test: edition-qualified *hypothesis* only, never auto-remap Coptic OT."""
import unittest

from tests.live_issue95_zechariah import propose_bohairic_zechariah_target


class BohairicZechariahHypothesisTests(unittest.TestCase):
    def test_four_horns_are_a_strict_source_edition_window(self):
        cts = "urn:cts:copticLit:ot.zach.bohairic_ed:01"
        for verse in range(18, 22):
            with self.subTest(verse=verse):
                self.assertEqual(
                    propose_bohairic_zechariah_target("bohairic.ot", cts, 1, verse),
                    (2, verse - 17),
                )

    def test_bohairic_second_chapter_is_distinct_numbering_window(self):
        cts = "urn:cts:copticLit:ot.zach.bohairic_ed:02"
        for verse in range(1, 7):
            with self.subTest(verse=verse):
                self.assertEqual(
                    propose_bohairic_zechariah_target("bohairic.ot", cts, 2, verse),
                    (2, verse + 4),
                )

    def test_wrong_source_work_edition_or_chapter_never_inherits_hypothesis(self):
        for corpus, cts, chapter, verse in (
            ("sahidic.ot", "urn:cts:copticLit:ot.zech.coptot:1", 1, 18),
            ("sahidic.ot", "urn:cts:copticLit:ot.zech.coptot:2", 2, 1),
            ("bohairic.ot", "urn:cts:copticLit:ot.zach.other_ed:1", 1, 18),
            ("bohairic.ot", "urn:cts:copticLit:ot.zech.bohairic_ed:1", 1, 18),
            ("bohairic.ot", "urn:cts:copticLit:ot.zach.bohairic_ed:2", 1, 18),
            ("bohairic.ot", "urn:cts:copticLit:ot.zach.bohairic_ed:1", 1, 17),
            ("bohairic.ot", "urn:cts:copticLit:ot.zach.bohairic_ed:1", 1, 22),
            ("bohairic.ot", "urn:cts:copticLit:ot.zach.bohairic_ed:2", 2, 7),
            ("bohairic-jonah", "urn:cts:copticLit:ot.zach.bohairic_ed:1", 1, 18),
            ("bohairic.ot", None, 1, 18),
        ):
            with self.subTest(corpus=corpus, cts=cts, chapter=chapter, verse=verse):
                self.assertIsNone(
                    propose_bohairic_zechariah_target(corpus, cts, chapter, verse)
                )


if __name__ == "__main__":
    unittest.main()
