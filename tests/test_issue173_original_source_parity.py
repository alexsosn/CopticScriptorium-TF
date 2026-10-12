"""#173 independent original Horner and existing translation source forgery tests."""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from live_issue173_full_native import compare_original_horner


class OriginalHornerParityTests(unittest.TestCase):
    def test_horner_and_translation_crossed_opening_retains_both_values(self):
        raw=(b'<trans_horner trans_horner="Horner &amp; corrected">'
             b'<translation translation="Other English">'
             b'<norm>a</norm></trans_horner><norm>b</norm></translation>')
        got=compare_original_horner(
            [("demo/demo:one",raw)],
            {("demo/demo:one",1):("trans_horner","Horner & corrected",0,1)},
            expected_counts={"trans_horner":1},
        )
        self.assertEqual(got["outside_translation_at_opening"],1)
        self.assertEqual(got["source_counts"],{"trans_horner":1})

    def test_same_count_wrong_original_or_missing_ellipsis_fails(self):
        raw=b'<trans_horner trans_horner="..."><norm>a</norm></trans_horner>'
        for wrong in (
            ("trans_horner","",0,1),
            ("trans_horner","...",0,2),
            ("translation","...",0,1),
        ):
            with self.subTest(wrong=wrong),self.assertRaisesRegex(ValueError,"mismatch"):
                compare_original_horner(
                    [("demo/demo:one",raw)],{("demo/demo:one",1):wrong},
                    expected_counts={"trans_horner":1},
                )
        self.assertEqual(compare_original_horner(
            [("demo/demo:one",raw)],
            {("demo/demo:one",1):("trans_horner","...",0,1)},
            expected_counts={"trans_horner":1})["source_counts"],{"trans_horner":1})

    def test_missing_attribute_duplicate_source_or_unclosed_fail(self):
        for raw in (
            b'<trans_horner horner="x"><norm>a</norm></trans_horner>',
            b'<trans_horner trans_horner="x" extra="y"><norm>a</norm></trans_horner>',
            b'<trans_horner trans_horner="x" trans_horner="y"></trans_horner>',
            b'</trans_horner>',
            b'<trans_horner trans_horner="x"><norm>a</norm>',
        ):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                compare_original_horner([("demo/demo:one",raw)],{},expected_counts={})

    def test_standalone_script_outside_repo(self):
        runner=Path(__file__).resolve().parents[1]/"tests/live_issue173_full_native.py"
        env=os.environ.copy()
        env.pop("PYTHONPATH",None)
        with TemporaryDirectory() as d:
            p=subprocess.run([sys.executable,str(runner)],cwd=d,env=env,
                             capture_output=True,text=True,check=False)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("usage: python tests/live_issue173_full_native.py",p.stderr)
        self.assertNotIn("ModuleNotFoundError",p.stderr)


if __name__=="__main__":
    unittest.main()
