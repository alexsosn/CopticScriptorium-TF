"""RED #153: reject forged original editorial source literal/offset evidence."""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from live_issue153_full_native import compare_source_editorial_events


class EditorialParityTest(unittest.TestCase):
    def test_crossed_source_annotations_exact_original_kind_value_and_boundary(self):
        raw = (
            b'<gap_reason gap_reason="lost"><gap_quantity gap_quantity="2">'
            b'<norm norm="a">a</norm></gap_reason><norm norm="b">b</norm>'
            b'</gap_quantity>'
        )
        observed = compare_source_editorial_events(
            [("fixture/fixture:one",raw)],
            {
                ("fixture/fixture:one",1):("gap_reason","lost",0,1),
                ("fixture/fixture:one",2):("gap_quantity","2",0,2),
            },
            expected_counts={"gap_reason":1,"gap_quantity":1},
        )
        self.assertEqual(observed,{"gap_quantity":1,"gap_reason":1})

    def test_entity_decoded_and_ordinal_and_blank_value(self):
        source = b'<note note="a &amp; b"><norm>a</norm></note><hi_rend hi_rend=""></hi_rend>'
        observed = compare_source_editorial_events(
            [("fixture/fixture:one",source)],
            {
                ("fixture/fixture:one",1):("note","a & b",0,1),
                ("fixture/fixture:one",2):("hi_rend","",1,1),
            },
            expected_counts={"note":1,"hi_rend":1},
        )
        self.assertEqual(observed,{"hi_rend":1,"note":1})

    def test_same_count_but_modified_lit_or_boundary_is_rejected(self):
        source=b'<note note="red"><norm>a</norm></note>'
        for forged in [("note","blue",0,1),("hi_rend","red",0,1),
                       ("note","red",0,2)]:
            with self.subTest(forged=forged),self.assertRaisesRegex(ValueError,"mismatch"):
                compare_source_editorial_events(
                    [("fixture/fixture:one",source)],
                    {("fixture/fixture:one",1):forged},
                    expected_counts={"note":1},
                )

    def test_orphan_and_unclosed_original_source_fail_closed(self):
        for raw in [
            b'</note><norm>a</norm>',
            b'<note note="x"><norm>a</norm>',
        ]:
            with self.subTest(raw=raw),self.assertRaisesRegex(ValueError,"editorial"):
                compare_source_editorial_events(
                    [("fixture/fixture:one",raw)],{},
                    expected_counts={},
                )

    def test_direct_pinned_auditor_script_can_import_from_outside_repo(self):
        runner=Path(__file__).resolve().parents[1]/"tests/live_issue153_full_native.py"
        env=os.environ.copy()
        env.pop("PYTHONPATH",None)
        with TemporaryDirectory() as outside:
            p=subprocess.run(
                [sys.executable,str(runner)],cwd=outside,env=env,
                capture_output=True,text=True,check=False,
            )
        self.assertNotEqual(p.returncode,0)
        self.assertIn("usage: python tests/live_issue153_full_native.py",p.stderr)
        self.assertNotIn("ModuleNotFoundError",p.stderr)


if __name__=="__main__":
    unittest.main()
