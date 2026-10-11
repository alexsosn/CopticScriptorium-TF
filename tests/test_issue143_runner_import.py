"""#143 RED: pinned full-native gate must run as a direct script without a package install."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


class PinnedNativeRunnerImportTests(unittest.TestCase):
    def test_a_direct_cli_call_from_outside_repo_reaches_usage_not_import_error(self):
        runner = Path(__file__).resolve().parents[1] / "tests/live_issue143_full_native.py"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        with TemporaryDirectory() as outside:
            p = subprocess.run(
                [sys.executable, str(runner)],
                cwd=outside, env=env, capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(p.returncode, 0, "no corpus arguments should be rejected")
        self.assertIn("usage: python tests/live_issue143_full_native.py", p.stderr)
        self.assertNotIn("ModuleNotFoundError", p.stderr)


if __name__ == "__main__":
    unittest.main()
