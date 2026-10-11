"""RED-first contract: #130 inverse query must be proven on authentic parent data.

This alone is not acceptance: GitHub Actions must run the live test on exact
immutable Coptic TT and CenterBLC/LXX release revisions.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeInverseQueryRealDataGate(unittest.TestCase):
    def test_real_parent_job_runs_with_both_exact_source_revisions(self):
        source = (ROOT / ".github/workflows/issue130-real-inverse-query.yml").read_text()
        for expected in (
            "309",  # Must check source-code SHA dynamically, not hard-code PR head.
            "CopticScriptorium/corpora",
            "3ac067f1709a0012daf39ea8da2fac79980176a5",
            "CenterBLC/LXX",
            "f32a98eddf7eb239aa73ab863d70381e416d5076",
            "tests/live_issue130_real_witnesses.py",
            "text-fabric==13.1.0",
            "github.event.pull_request.head.sha || github.sha",
        ):
            if expected == "309":
                self.assertIn('git rev-parse HEAD', source)
            else:
                self.assertIn(expected, source)

    def test_real_parent_smoke_uses_actual_tf_inverse_index_and_two_jonah_witnesses(self):
        source = (ROOT / "tests/live_issue130_real_witnesses.py").read_text()
        for required in (
            "project_reference_modules(",
            "validate_lxx_release(",
            "verify_coptic_module_parent(",
            "find_coptic_witnesses(",
            "Jonah",
            "bohairic-jonah",
            "sahidic.jonah",
            "Ruth",
            "Hab",
            "count",
            "source_word_ordinals",
        ):
            with self.subTest(marker=required):
                self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main()
