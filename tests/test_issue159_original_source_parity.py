"""#159 adverse source identity and forged ontology label rejection."""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from live_issue159_full_native import compare_source_entity_labels


class EntityLabelSourceAdversarialTests(unittest.TestCase):
    def test_crossed_source_wrappers_and_preserved_original_literal(self):
        raw=(
            b'<entity_text entity_text="a b"><entity_head_tok entity_head_tok="#u2">'
            b'<norm>a</norm></entity_text><norm>b</norm></entity_head_tok>'
        )
        self.assertEqual(compare_source_entity_labels([
            ("demo/demo:one",raw)
        ],{
            ("demo/demo:one",1):("entity_text","a b",0,1),
            ("demo/demo:one",2):("entity_head_tok","#u2",0,2),
        },expected_counts={"entity_text":1,"entity_head_tok":1}),{
            "entity_head_tok":1,"entity_text":1
        })

    def test_source_ontology_looking_ref_not_promoted_or_rewritten(self):
        raw=b'<placeName_ref placeName_ref="paths:places:32"><norm>a</norm></placeName_ref>'
        self.assertEqual(compare_source_entity_labels([
            ("demo/demo:one",raw)
        ],{
            ("demo/demo:one",1):("placeName_ref","paths:places:32",0,1)
        },expected_counts={"placeName_ref":1}),{"placeName_ref":1})
        for forged in (
            ("placeName_ref","wd:Q32",0,1),
            ("placeName_ref","paths:places:32",0,2),
            ("placeName_type","paths:places:32",0,1),
        ):
            with self.subTest(forged=forged),self.assertRaisesRegex(ValueError,"mismatch"):
                compare_source_entity_labels([
                    ("demo/demo:one",raw)
                ],{("demo/demo:one",1):forged},
                expected_counts={"placeName_ref":1})

    def test_duplicate_missing_and_unclosed_pairs_fail_closed(self):
        samples=(
            b'<entity_identity entity_identity="Sarah"><norm>a</norm>',
            b'</entity_identity>',
            b'<placeName_ref><norm>a</norm></placeName_ref>',
            b'<entity_identity entity_identity="a" entity_identity="b"></entity_identity>',
        )
        for raw in samples:
            with self.subTest(raw=raw),self.assertRaisesRegex(ValueError,"entity label"):
                compare_source_entity_labels([("demo/demo:one",raw)],{},expected_counts={})

    def test_full_native_auditor_direct_run_without_repo_cwd_or_pythonpath(self):
        runner=Path(__file__).resolve().parents[1]/"tests/live_issue159_full_native.py"
        env=os.environ.copy()
        env.pop("PYTHONPATH",None)
        with TemporaryDirectory() as outside:
            p=subprocess.run([sys.executable,str(runner)],cwd=outside,env=env,
                             capture_output=True,text=True,check=False)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("usage: python tests/live_issue159_full_native.py",p.stderr)
        self.assertNotIn("ModuleNotFoundError",p.stderr)


if __name__=="__main__":
    unittest.main()
