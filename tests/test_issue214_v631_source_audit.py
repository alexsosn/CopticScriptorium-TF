"""#214 — RED-first v6.3.1 corrected TT source literal-conservation contract.

These unit cases are synthetic negative controls. A separate pinned source
smoke must prove the same claims on all *four* immutable original TT blobs.
"""
from __future__ import annotations

from pathlib import Path
import json
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tests" / "live_issue214_v631_source_audit.py"
WORKFLOW = ROOT / ".github" / "workflows" / "issue177-agent-user-smoke.yml"
NEW_COMMIT = "6fb51458e7156dd5387c2b2dca207aac1692e4d0"
OLD_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"


class CorrectedUpstreamTTReleaseTests(unittest.TestCase):
    def audit(self):
        self.assertTrue(AUDIT.is_file(), "RED: source-literal conservation audit missing")
        return runpy.run_path(str(AUDIT))

    def test_exact_upstream_release_blob_pin_and_four_source_paths(self):
        scope = self.audit()
        self.assertEqual(scope["OLD_COMMIT"], OLD_COMMIT)
        self.assertEqual(scope["NEW_COMMIT"], NEW_COMMIT)
        blobs = scope["CHANGED_BLOBS"]
        self.assertEqual(len(blobs), 4)
        self.assertEqual(
            set(blobs),
            {
                "john-constantinople/john.constantinople_TT/penitence.01.tt",
                "john-constantinople/john.constantinople_TT/penitence.02.tt",
                "proclus-homilies/proclus.homilies_TT/proclus.23.nativity.tt",
                "shenoute-those/shenoute.those_TT/shenoute.those.GL269-270.tt",
            },
        )
        for item in blobs.values():
            self.assertEqual(len(item), 2)
            self.assertTrue(all(len(sha) == 40 for sha in item))

    def test_only_exact_spurious_norm_wrappers_and_meta_version_may_change(self):
        compare = self.audit()["compare_original_tt"]
        original = (
            '<meta version_date="2026-06-08" version_n="6.3.0">\n'
            '<orig_group orig_group="ⲁⲃ">\n'
            '<norm_group norm_group="ⲁⲃ">\n'
            '<norm xml:id="u1" func="root" norm="ⲁ">\n'
            '<norm_func norm_func="root">\n'
            'ⲁ\n'
            '</norm_func>\n'
            '</norm>\n'
            '</norm_group>\n'
            '</orig_group>\n'
            '</meta>\n'
        )
        corrected = (
            '<meta version_date="2026-10-26" version_n="6.3.1">\n'
            '<orig_group orig_group="ⲁⲃ">\n'
            '<norm_group norm_group="ⲁⲃ">\n'
            '<norm xml:id="u1" func="root" norm="ⲁ">\n'
            'ⲁ\n'
            '</norm>\n'
            '</norm_group>\n'
            '</orig_group>\n'
            '</meta>\n'
        )
        result = compare(original.encode("utf-8"), corrected.encode("utf-8"))
        self.assertEqual(result["original_norm_count"], 1)
        self.assertEqual(result["new_norm_count"], 1)
        self.assertEqual(result["removed_wrappers"]["norm_func"], 2)
        self.assertEqual(result["retained_source_content"], "exact")
        for tampered in (
            corrected.replace('norm="ⲁ"', 'norm="ⲃ"'),
            corrected.replace('<norm_group', '<orig_group'),
            corrected.replace('ⲁ\n', 'ⲃ\n'),
            corrected.replace('</norm>', '</norm_func>'),
            corrected.replace('version_n="6.3.1"', 'version_n="6.3.0"'),
        ):
            with self.subTest(tampered=tampered[-100:]):
                with self.assertRaises(ValueError):
                    compare(original.encode("utf-8"), tampered.encode("utf-8"))

    def test_current_producer_manifest_and_historical_agora_run_are_not_conflated(self):
        root = ROOT
        manifest = json.loads((root / "agora.materializer.json").read_text(encoding="utf-8"))
        source = next(x for x in manifest["materializers"][0]["acquisition"] if x["type"] == "git")
        self.assertEqual(source["ref"], NEW_COMMIT)
        readme = (root / "README.md").read_text(encoding="utf-8")
        quick = (root / "docs/researcher-quickstart.md").read_text(encoding="utf-8")
        guide = (root / "docs/researcher-guide.md").read_text(encoding="utf-8")
        self.assertIn("Agora #310", readme)
        self.assertIn("Agora #310", quick)
        self.assertIn("Agora #310", guide)
        self.assertIn(NEW_COMMIT, readme)
        self.assertIn(OLD_COMMIT, readme)
        self.assertIn("previous", quick)
        self.assertIn("not yet", readme)
        self.assertIn("separate", guide)

    def test_existing_installed_wheel_smoke_runs_full_four_file_delta(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(OLD_COMMIT, workflow)
        self.assertIn(NEW_COMMIT, workflow)
        self.assertIn("live_issue214_v631_source_audit.py", workflow)
        self.assertIn("tests.test_issue214_v631_source_audit", workflow)
        self.assertIn("--upstream-commit", AUDIT.read_text(encoding="utf-8"))
        self.assertNotIn("print(source_text)", AUDIT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
