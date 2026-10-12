"""Issue #173 independent source English witness falsification and boundary tests."""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from live_issue173_full_native import compare_original_horner_sources

class SourceHornerAdversarial(unittest.TestCase):
    def test_english_horner_is_not_alias_of_existing_english_translation(self):
        raw=(b'<translation translation="IT came to pass, when Jesus had risen">'
             b'<trans_horner trans_horner="But it happened after that Jesus rose">'
             b'<norm>a</norm></translation><norm>b</norm></trans_horner>')
        self.assertEqual(compare_original_horner_sources(
            [("demo/demo:one",raw)],
            {("demo/demo:one",1):("trans_horner","But it happened after that Jesus rose",0,2)},
            expected_counts={"trans_horner":1}),{"trans_horner":1})

    def test_english_entity_decode_once_and_forged_literal_or_position_rejected(self):
        raw=b'<trans_horner trans_horner="a &amp; b"><norm>a</norm></trans_horner>'
        good={("demo/demo:one",1):("trans_horner","a & b",0,1)}
        self.assertEqual(compare_original_horner_sources(
            [("demo/demo:one",raw)],good,expected_counts={"trans_horner":1}),
            {"trans_horner":1})
        for bad in (
            ("trans_horner","a &amp; b",0,1),
            ("trans_horner","a & b",0,2),
            ("translation","a & b",0,1),
        ):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,"mismatch"):
                compare_original_horner_sources(
                    [("demo/demo:one",raw)],{("demo/demo:one",1):bad},
                    expected_counts={"trans_horner":1})

    def test_orphan_missing_or_unclosed_original_rejected(self):
        for raw in (
            b'</trans_horner>',
            b'<trans_horner><norm>a</norm></trans_horner>',
            b'<trans_horner trans_horner="English"><norm>a</norm>',
        ):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                compare_original_horner_sources([("demo/demo:one",raw)],{},expected_counts={})

    def test_runner_imports_outside_repo(self):
        runner=Path(__file__).resolve().parents[1]/"tests/live_issue173_full_native.py"
        env=os.environ.copy()
        env.pop("PYTHONPATH",None)
        with TemporaryDirectory() as td:
            p=subprocess.run([sys.executable,str(runner)],cwd=td,env=env,
                             capture_output=True,text=True,check=False)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("usage: python tests/live_issue173_full_native.py",p.stderr)
        self.assertNotIn("ModuleNotFoundError",p.stderr)

if __name__=="__main__":
    unittest.main()
