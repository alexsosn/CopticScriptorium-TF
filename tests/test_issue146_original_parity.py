"""#146 RED adverse original source-to-native reference evidence."""
import unittest
from live_issue146_full_native import compare_source_reference_events

def raw(source):
    return source.encode("utf-8")

class ReferenceSourceAdversarialTests(unittest.TestCase):
    def test_nested_crossed_literal_and_source_offsets(self):
        src=raw('<chapter_n chapter_n="148_postscript">'
                '<marcion_verse_n marcion_verse_n="21">'
                '<norm norm="a">a</norm></chapter_n>'
                '<norm norm="b">b</norm></marcion_verse_n>')
        observed=compare_source_reference_events(
            [("fixture/fixture:one",src)],
            {
                ("fixture/fixture:one",1):("chapter_n","148_postscript",0,1),
                ("fixture/fixture:one",2):("marcion_verse_n","21",0,2),
            },
            expected_counts={"chapter_n":1,"marcion_verse_n":1},
        )
        self.assertEqual(observed,{"chapter_n":1,"marcion_verse_n":1})
        with self.assertRaisesRegex(ValueError,"inventory"):
            compare_source_reference_events(
                [("fixture/fixture:one",src)],
                {
                    ("fixture/fixture:one",1):("chapter_n","148_postscript",0,1),
                    ("fixture/fixture:one",2):("marcion_verse_n","21",0,2),
                },
            )

    def test_forged_literal_or_word_boundary_cannot_pass(self):
        raw_tt=raw('<chapter_n chapter_n="0"><norm>a</norm></chapter_n>')
        for bad in [
            ("chapter_n","1",0,1),("chapter_n","0",0,2),
            ("petermann_chapter_n","0",0,1),
        ]:
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError,"mismatch"):
                compare_source_reference_events([
                    ("fixture/fixture:one",raw_tt)
                ],{("fixture/fixture:one",1):bad})

    def test_orphan_and_unclosed_source_references_fail(self):
        for bad in [
            "</chapter_n><norm>a</norm>",
            "<chapter_n chapter_n=\"1\"><norm>a</norm>",
        ]:
            with self.subTest(src=bad), self.assertRaisesRegex(ValueError,"reference"):
                compare_source_reference_events([("fixture/fixture:one",raw(bad))],{})
