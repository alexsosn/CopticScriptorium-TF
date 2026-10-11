"""RED: researcher-facing release status must reflect verified merged capabilities.

Guards against the previously stale claim that no native TF converter or
registered Agora remote-source end-to-end path existed. Uses real user docs.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CurrentDocsStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.known = (ROOT / "KNOWN-ISSUES.md").read_text(encoding="utf-8")
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_implemented_converter_not_mislabeled_as_research_only(self):
        for obsolete in (
            "Production converter behavior has not been implemented",
            "Canonical source representation is not yet established",
            "Document identity and overlap semantics are not yet established",
            "Text-Fabric slot and section models are not yet established",
            "Corpus scale has not yet been budgeted",
        ):
            with self.subTest(obsolete=obsolete):
                self.assertNotIn(obsolete, self.known)
        for evidence in ("native Text-Fabric", "word", "document", "pinned",
                         "CoNLL-U", "license", "Context-Fabric", "LXX"):
            with self.subTest(evidence=evidence):
                self.assertIn(evidence, self.known)

    def test_registered_full_remote_source_acceptance_is_reported_truthfully(self):
        for source in (self.known, self.readme):
            for marker in ("Agora", "PR #215", "CopticScriptorium/corpora",
                           "3ac067f1709a0012daf39ea8da2fac79980176a5",
                           "explicit", "Context-Fabric"):
                with self.subTest(marker=marker):
                    self.assertIn(marker, source)
        self.assertNotIn("The registered integration is still incomplete", self.readme)
        self.assertNotIn("full-corpus end-to-end path **has not yet passed**", self.readme)
        self.assertNotIn("Registration and the", self.known)

    def test_manual_import_and_textual_equivalence_not_overclaimed(self):
        self.assertIn("does not automatically", self.readme)
        self.assertIn("candidate", self.known.lower())
        self.assertIn("word alignment", self.known.lower())
        self.assertIn("source licenses", self.known.lower())


if __name__ == "__main__":
    unittest.main()
