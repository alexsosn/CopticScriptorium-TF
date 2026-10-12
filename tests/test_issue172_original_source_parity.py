"""Issue #172 independently reject forged source keys, literal & position."""
from pathlib import Path
import os
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from live_issue172_full_native import compare_original_residuals


class ResidualOriginalParity(unittest.TestCase):
    def test_source_hi_uses_rend_not_hi(self):
        raw=b'<hi rend="red"><norm>a</norm></hi>'
        self.assertEqual(compare_original_residuals(
            [("demo/demo:one",raw)],
            {("demo/demo:one",1):("hi","red",0,1)},
            expected_counts={"hi":1}
        ),{"hi":1})
        for bad in (
            b'<hi hi="red"><norm>a</norm></hi>',
            b'<hi rend="red" hi="red"><norm>a</norm></hi>',
        ):
            with self.subTest(raw=bad),self.assertRaisesRegex(ValueError,"attribute"):
                compare_original_residuals([("demo/demo:one",bad)],{},expected_counts={})

    def test_crossed_figure_and_gap_originals_preserve_kind(self):
        raw=(b'<figDesc figDesc="seal"><figure figure="figure">'
             b'<norm>a</norm></figDesc><norm>b</norm></figure>')
        self.assertEqual(compare_original_residuals(
            [("demo/demo:one",raw)],{
                ("demo/demo:one",1):("figDesc","seal",0,1),
                ("demo/demo:one",2):("figure","figure",0,2),
            },expected_counts={"figDesc":1,"figure":1}),
            {"figDesc":1,"figure":1})

    def test_escaped_quote_literal_is_decoded_once_not_canonicalized(self):
        raw=b'<quote_ref quote_ref="Sal.72 &amp; 22.23"><norm>a</norm></quote_ref>'
        self.assertEqual(compare_original_residuals(
            [("demo/demo:one",raw)],
            {("demo/demo:one",1):("quote_ref","Sal.72 & 22.23",0,1)},
            expected_counts={"quote_ref":1}),{"quote_ref":1})
        for bad in (
            ("quote_ref","Sal.72 &amp; 22.23",0,1),
            ("quote_type","Sal.72 & 22.23",0,1),
            ("quote_ref","Sal.72 & 22.23",0,2),
        ):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,"mismatch"):
                compare_original_residuals(
                    [("demo/demo:one",raw)],{("demo/demo:one",1):bad},
                    expected_counts={"quote_ref":1})

    def test_unclosed_missing_or_orphan_original_rejected(self):
        for raw in (
            b'</figDesc>',
            b'<source_lang><norm>a</norm></source_lang>',
            b'<german german="x"><norm>a</norm>',
        ):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                compare_original_residuals([("demo/demo:one",raw)],{},expected_counts={})

    def test_standalone_script_can_import_outside_repo(self):
        runner=Path(__file__).resolve().parents[1]/"tests/live_issue172_full_native.py"
        env=os.environ.copy()
        env.pop("PYTHONPATH",None)
        with TemporaryDirectory() as td:
            p=subprocess.run([sys.executable,str(runner)],cwd=td,env=env,
                             capture_output=True,text=True,check=False)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("usage: python tests/live_issue172_full_native.py",p.stderr)
        self.assertNotIn("ModuleNotFoundError",p.stderr)


if __name__=="__main__":
    unittest.main()
