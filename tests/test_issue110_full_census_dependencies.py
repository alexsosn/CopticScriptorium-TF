"""Regression #110: full 2,628-record TF gate must install TF before reload.

Real CI run 38132112506/job 114448411135 reached the full converter after
successfully parsing pinned source data and failed: No module named tf.
This checks the full-census workflow, not the separate Mark-only job.
"""
from pathlib import Path
import unittest

class FullNativeCensusDependencyTests(unittest.TestCase):
    def test_full_census_installs_declared_tf_dependency_before_conversion(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/issue69-full-verse-census.yml").read_text(encoding="utf-8")
        install = "python -m pip install 'text-fabric==13.1.0'"
        conversion = "python research/issue-16/full_converter_smoke.py"
        self.assertIn(install, workflow)
        self.assertIn(conversion, workflow)
        self.assertLess(workflow.index(install), workflow.index(conversion))

    def test_dependency_pin_is_the_converter_declared_pin(self):
        pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('"text-fabric==13.1.0"', pyproject)

if __name__ == "__main__":
    unittest.main()
