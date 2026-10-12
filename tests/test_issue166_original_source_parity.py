"""Issue #166 adversarial original CTS/ref literal and boundary checks."""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from live_issue166_full_native import compare_original_alternate_references


class SourceReferenceParity(unittest.TestCase):
    def test_crossed_cts_and_human_labels_are_distinct(self):
        raw=(b'<verse_n_vid_n verse_n_vid_n="urn:cts:ot:1.1">'
             b'<verse_n_vname verse_n_vname="Jonah 1:1">'
             b'<norm>a</norm></verse_n_vid_n><norm>b</norm></verse_n_vname>')
        got=compare_original_alternate_references(
            [("demo/demo:one",raw)],{
                ("demo/demo:one",1):("verse_n_vid_n","urn:cts:ot:1.1",0,1),
                ("demo/demo:one",2):("verse_n_vname","Jonah 1:1",0,2),
            },expected_counts={"verse_n_vid_n":1,"verse_n_vname":1})
        self.assertEqual(got,{"verse_n_vid_n":1,"verse_n_vname":1})

    def test_html_entity_and_double_underscore_original_source(self):
        raw=b'<vid__n vid__n="a &amp; b"><norm>a</norm></vid__n>'
        self.assertEqual(compare_original_alternate_references(
            [("demo/demo:one",raw)],
            {("demo/demo:one",1):("vid__n","a & b",0,1)},
            expected_counts={"vid__n":1}),{"vid__n":1})
        for bad in (
            ("vid_n","a & b",0,1),
            ("vid__n","a &amp; b",0,1),
            ("vid__n","a & b",0,2),
        ):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,"mismatch"):
                compare_original_alternate_references(
                    [("demo/demo:one",raw)],{("demo/demo:one",1):bad},
                    expected_counts={"vid__n":1})

    def test_orphan_unclosed_and_no_literal_rejected(self):
        for raw in (
            b'</verse>',
            b'<chapter_name><norm>a</norm></chapter_name>',
            b'<verse verse="1"><norm>a</norm>',
        ):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                compare_original_alternate_references([("demo/demo:one",raw)],{},expected_counts={})

    def test_standalone_auditor_outside_repo_pythonpath(self):
        runner=Path(__file__).resolve().parents[1]/"tests/live_issue166_full_native.py"
        env=os.environ.copy()
        env.pop("PYTHONPATH",None)
        with TemporaryDirectory() as d:
            p=subprocess.run([sys.executable,str(runner)],cwd=d,env=env,
                             capture_output=True,text=True,check=False)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("usage: python tests/live_issue166_full_native.py",p.stderr)
        self.assertNotIn("ModuleNotFoundError",p.stderr)


if __name__=="__main__":
    unittest.main()
