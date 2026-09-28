"""RED-first packaging contracts for issue #43."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InstalledConsoleCommandTests(unittest.TestCase):
    def test_project_declares_console_command_as_existing_cli_main(self):
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            metadata["project"]["scripts"]["copticscriptorium-tf"],
            "copticscriptorium_tf.converter:main",
        )

    def test_module_cli_remains_available(self):
        completed = subprocess.run(
            [sys.executable, "-m", "copticscriptorium_tf.converter", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Convert supported Coptic Scriptorium TT sources", completed.stdout)


if __name__ == "__main__":
    unittest.main()
