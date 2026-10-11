"""RED-first workflow contract for issue #101: superseded heads are cancelled.

Cancel PR heads of the *same* workflow and PR only. Never share a group for
non-PR runs: GitHub also replaces older pending runs on group collisions even
when cancel-in-progress is false. A unique run_id fallback is required.
"""
from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREVIOUSLY_UNCANCELLED = (
    "issue17-agora.yml",
    "issue43-console-command.yml",
    "issue69-full-verse-census.yml",
    "issue69-pinned-verses.yml",
    "issue70-real-lxx.yml",
    "issue73-dual-lxx-modules.yml",
    "issue75-ot-inventory.yml",
    "issue78-multiwork-lxx.yml",
    "issue80-lxx-coverage.yml",
    "issue82-full-streamed-lxx.yml",
    "issue89-dual-native-modules.yml",
    "issue95-zechariah.yml",
    "issue97-crosswalk.yml",
    "issue97-zechariah-sequences.yml",
)

EXPECTED_GROUP = "  group: ${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.event.pull_request.number || github.run_id }}"
EXPECTED_CANCEL = "  cancel-in-progress: ${{ github.event_name == 'pull_request' }}"


class SupersededHeadCancellationTests(unittest.TestCase):
    def test_each_previously_unprotected_workflow_is_scoped_and_pr_only(self):
        names = set()
        for basename in PREVIOUSLY_UNCANCELLED:
            with self.subTest(workflow=basename):
                contents = (ROOT / ".github/workflows" / basename).read_text(
                    encoding="utf-8"
                )
                self.assertIn("\non:\n", contents)
                self.assertIn("\n  pull_request:", contents)
                self.assertIn("\npermissions:\n", contents)
                self.assertIn("\njobs:\n", contents)
                self.assertEqual(
                    contents.count("\nconcurrency:\n"),
                    1,
                    "one top-level concurrency policy is required",
                )
                before, after = contents.split("\nconcurrency:\n")
                self.assertIn("\n  pull_request:", before)
                block, rest = after.split("\npermissions:\n", 1)
                self.assertEqual(
                    block.strip("\n").splitlines(),
                    [EXPECTED_GROUP, EXPECTED_CANCEL],
                    "exact workflow-scoped group and PR-only cancellation",
                )
                self.assertIn("\njobs:\n", "\npermissions:\n" + rest)
                name = contents.split("name: ", 1)[1].split("\n", 1)[0]
                self.assertNotIn(name, names, "workflow names must be distinct")
                names.add(name)

    def test_all_source_heavy_workflows_are_covered(self):
        # Adding a new source-heavy workflow without a cancellation policy is
        # a measurable CI cost regression. Check current explicit inventory.
        directory = ROOT / ".github/workflows"
        for path in directory.glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            if "repository: CopticScriptorium/corpora" in text:
                with self.subTest(workflow=path.name):
                    self.assertIn(
                        "\nconcurrency:\n",
                        text,
                        "source-acquiring workflow has no cancellation policy",
                    )


if __name__ == "__main__":
    unittest.main()
