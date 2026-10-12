"""#162 independent raw source-forged editorial/page reference rejection tests."""
from pathlib import Path
import subprocess
import sys
import os
from tempfile import TemporaryDirectory
import unittest

from live_issue162_full_native import compare_original_document_sources


class DocumentMarkersSourceAdversarial(unittest.TestCase):
    def test_source_coptic_combining_and_roman_label_opening_ordinals(self):
        raw='<pb_coptic_id pb_coptic_id="ⲧ̅ⲛ̅ⲃ̅.ⲁ."><p_n p_n="I.1"><norm>a</norm></pb_coptic_id><norm>b</norm></p_n>'.encode()
        self.assertEqual(compare_original_document_sources(
            [("demo/demo:one",raw)],{
                ("demo/demo:one",1):("pb_coptic_id","ⲧ̅ⲛ̅ⲃ̅.ⲁ.",0,1),
                ("demo/demo:one",2):("p_n","I.1",0,2),
            },expected_counts={"pb_coptic_id":1,"p_n":1},
        ),{"p_n":1,"pb_coptic_id":1})

    def test_source_xml_decoded_once_and_blank_literal_retained(self):
        raw=b'<p_source p_source="A &amp; B"><norm>a</norm></p_source><p p=""></p>'
        self.assertEqual(compare_original_document_sources(
            [("demo/demo:one",raw)],{
                ("demo/demo:one",1):("p_source","A & B",0,1),
                ("demo/demo:one",2):("p","",1,1),
            },expected_counts={"p_source":1,"p":1},
        ),{"p":1,"p_source":1})

    def test_same_count_forged_value_kind_or_offsets_fail_closed(self):
        raw=b'<p_n p_n="I.1"><norm>a</norm></p_n>'
        for bad in [
            ("p_n","1",0,1),("p","I.1",0,1),("p_n","I.1",0,2),
        ]:
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,"mismatch"):
                compare_original_document_sources(
                    [("demo/demo:one",raw)],
                    {("demo/demo:one",1):bad},
                    expected_counts={"p_n":1},
                )

    def test_missing_unclosed_orphan_fail_closed(self):
        for raw in (
            b'<p_n><norm>a</norm></p_n>',
            b'<p_n p_n="1"><norm>a</norm>',
            b'</p_n>',
        ):
            with self.subTest(raw=raw),self.assertRaisesRegex(ValueError,"page/paragraph"):
                compare_original_document_sources(
                    [("demo/demo:one",raw)],{},expected_counts={}
                )

    def test_outside_repo_cwd_bootstraps_original_source_auditor(self):
        runner=Path(__file__).resolve().parents[1]/"tests/live_issue162_full_native.py"
        env=os.environ.copy()
        env.pop("PYTHONPATH",None)
        with TemporaryDirectory() as tmp:
            p=subprocess.run([sys.executable,str(runner)],cwd=tmp,env=env,
                             capture_output=True,text=True,check=False)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("usage: python tests/live_issue162_full_native.py",p.stderr)
        self.assertNotIn("ModuleNotFoundError",p.stderr)


if __name__=="__main__":
    unittest.main()
