"""Regression: versioned versification edits must trigger full pinned corpus gates.

A 17-verse edition-specific crosswalk changes both native TF module membership
and coverage status distribution; a small real Zechariah pilot alone cannot
certify all 2,394,354 source word statuses after the change.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "'copticscriptorium_tf/lxx_versification.py'"


class VersionedCrosswalkWorkflowTests(unittest.TestCase):
    def test_full_streamed_modules_ci_runs_on_edition_rule_changes(self):
        data = (ROOT / ".github/workflows/issue82-full-streamed-lxx.yml").read_text()
        self.assertIn(SOURCE, data.split("  workflow_dispatch:", 1)[0])
        self.assertIn("tests/live_issue82_full_modules.py", data)

    def test_full_reference_coverage_ci_runs_on_edition_rule_changes(self):
        data = (ROOT / ".github/workflows/issue80-lxx-coverage.yml").read_text()
        self.assertIn(SOURCE, data.split("  workflow_dispatch:", 1)[0])
        self.assertIn("tests/live_issue80_full_lxx_coverage.py", data)


if __name__ == "__main__":
    unittest.main()
