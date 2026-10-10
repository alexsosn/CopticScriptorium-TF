"""RED-first researched Coptic↔LXX full-corpus researcher guide contract (#86).

Review code + pinned full real CI evidence if updating the numeric baseline;
do not mistake address candidates for established Greek/Coptic equivalence.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/coptic-lxx-alignment.md"


class CopticLxxGuideCoverageTests(unittest.TestCase):
    def test_full_scope_and_provenance_are_distinguished_from_three_book_pilot(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertNotIn("current\npilot knows three source families", text)
        self.assertNotIn("only three source families", text)
        for marker in (
            "2,628", "2,394,354", "21,120", "1,072,234",
            "1,309,117", "12,951", "52",
            "reference_candidate", "unclassified_corpus",
            "unresolved", "ambiguous",
            "3ac067f1709a0012daf39ea8da2fac79980176a5",
            "f32a98eddf7eb239aa73ab863d70381e416d5076",
            "38080479109",
            "source_sha256",
            "source_record_id",
            "reference addresses", "not", "textual equivalence",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_edition_and_source_scope_remain_explicit(self):
        text = GUIDE.read_text(encoding="utf-8")
        for marker in (
            "OT", "NT", "undetermined", "versification",
            "full conversion", "7.1 GiB", "9:48",
            "CenterBLC/LXX", "CopticScriptorium/corpora",
            "native", "weft",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
