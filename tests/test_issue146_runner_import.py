"""RED(#146): full pinned corpus auditor must run from outside repository cwd."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


class ReferenceNativeRunnerImportTests(unittest.TestCase):
    def test_direct_script_has_self_contained_repo_import_before_parsing_arguments(self):
        runner = Path(__file__).resolve().parents[1] / "tests/live_issue146_full_native.py"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        with TemporaryDirectory() as td:
            p = subprocess.run(
                [sys.executable, str(runner)],
                cwd=td, env=env, capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(p.returncode, 0, "missing source args must not succeed")
        self.assertIn("usage: python tests/live_issue146_full_native.py", p.stderr)
        self.assertNotIn("ModuleNotFoundError", p.stderr)


if __name__ == "__main__":
    unittest.main()
