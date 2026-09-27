"""RED-first installed CLI packaging contract for issue #43."""
from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InstalledCliContractTests(unittest.TestCase):
    def test_project_exposes_reviewed_converter_console_script(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(
            project.get("scripts", {}).get("copticscriptorium-tf"),
            "copticscriptorium_tf.converter:main",
        )


if __name__ == "__main__":
    unittest.main()
