"""#156 source-original adversarial forged multi-attributes and run-path checks."""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from live_issue156_full_native import compare_source_interventions


class OriginalMultiattrAuditTests(unittest.TestCase):
    def test_crossed_original_source_and_exact_multiattrs(self):
        raw=(
            b'<gap reason="lost" unit="char">'
            b'<supplied supplied="yes" source="transcriber">'
            b'<norm>a</norm></gap><norm>b</norm></supplied>'
        )
        self.assertEqual(compare_source_interventions(
            [("demo/demo:one",raw)],{
                ("demo/demo:one",1):(
                    "gap","",(("reason","lost"),("unit","char")),0,1),
                ("demo/demo:one",2):(
                    "supplied","yes",(("source","transcriber"),("supplied","yes")),0,2),
            },expected_counts={"gap":1,"supplied":1},
        ),{"gap":1,"supplied":1})

    def test_missing_vs_present_empty_and_absence_of_abbr_named_attr(self):
        raw=b'<abbr type=""><norm>a</norm></abbr><gap extent="2"><norm>b</norm></gap>'
        self.assertEqual(compare_source_interventions(
            [("demo/demo:one",raw)],{
                ("demo/demo:one",1):("abbr","",(("type",""),),0,1),
                ("demo/demo:one",2):("gap","",(("extent","2"),),1,2),
            },expected_counts={"abbr":1,"gap":1},
        ),{"abbr":1,"gap":1})

    def test_wrong_extra_or_missing_attribute_does_not_pass_even_with_same_count(self):
        raw=b'<gap gap="gap" extent="2"><norm>a</norm></gap>'
        bads=[
            ("gap","gap",(("gap","gap"),),0,1),
            ("gap","gap",(("extent","3"),("gap","gap")),0,1),
            ("gap","gap",(("extent","2"),("gap","gap")),0,2),
        ]
        for bad in bads:
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,"mismatch"):
                compare_source_interventions(
                    [("demo/demo:one",raw)],
                    {("demo/demo:one",1):bad},
                    expected_counts={"gap":1},
                )

    def test_duplicate_unclosed_orphan_and_unknown_attributes_fail_closed(self):
        for raw in (
            b'<gap gap="a" gap="b"></gap>',
            b'<gap impossible="1"></gap>',
            b'<abbr type="a">',
            b'</supplied>',
        ):
            with self.subTest(raw=raw),self.assertRaisesRegex(ValueError,"attribute|intervention"):
                compare_source_interventions([("demo/demo:one",raw)],{},expected_counts={})

    def test_direct_pinned_source_auditor_runs_outside_repo_without_pythonpath(self):
        runner=Path(__file__).resolve().parents[1]/"tests/live_issue156_full_native.py"
        env=os.environ.copy()
        env.pop("PYTHONPATH",None)
        with TemporaryDirectory() as d:
            p=subprocess.run([sys.executable,str(runner)],cwd=d,env=env,
                             capture_output=True,text=True,check=False)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("usage: python tests/live_issue156_full_native.py",p.stderr)
        self.assertNotIn("ModuleNotFoundError",p.stderr)


if __name__=="__main__":
    unittest.main()
