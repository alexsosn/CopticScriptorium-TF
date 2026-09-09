import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "cross_format_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_cross_format", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load cross-format audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TT = '''<meta corpus="demo" document_cts_urn="urn:cts:demo:one">
<norm xml:id="u1" func="root" pos="V" lemma="ⲁ" norm="ⲁ">ⲁ</norm>
<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="ⲃ" norm="ⲃ">ⲃ</norm>
'''

CONLLU = '''# newdoc id = demo:one
# sent_id = demo-one_s0001
# text = ⲁ ⲃ
1	ⲁ	ⲁ	VERB	V	Mood=Ind	0	root	_	Cxn=Demo
2	ⲃ	ⲃ	NOUN	N	Gender=Masc	1	obj	_	_
'''


class CrossFormatAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_pairs_case_variant_record_names_and_compares_shared_token_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "demo" / "demo_TT"
            conllu_dir = root / "demo" / "demo_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)
            (tt_dir / "AP.One.tt").write_text(TT, encoding="utf-8")
            (conllu_dir / "ap.one.conllu").write_text(CONLLU, encoding="utf-8")

            report = self.audit.audit_upstream(root)

        self.assertEqual(report["tt_document_count"], 1)
        self.assertEqual(report["conllu_document_count"], 1)
        self.assertEqual(report["paired_document_count"], 1)
        self.assertEqual(report["compared_document_count"], 1)
        self.assertEqual(report["conllu_placeholder_count"], 0)
        self.assertEqual(report["conllu_placeholders"], [])
        self.assertEqual(report["tt_only"], [])
        self.assertEqual(report["conllu_only"], [])
        self.assertEqual(report["token_count_mismatches"], [])
        self.assertEqual(
            report["field_mismatch_counts"],
            {"func": 0, "head": 0, "lemma": 0, "norm": 0, "pos": 0},
        )
        self.assertEqual(
            report["case_variant_pairs"],
            [
                {
                    "dataset": "demo/demo",
                    "tt_record": "AP.One",
                    "conllu_record": "ap.one",
                }
            ],
        )

    def test_reads_tt_from_dataset_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "packed"
            conllu_dir = corpus / "packed_CONLLU"
            conllu_dir.mkdir(parents=True)
            (conllu_dir / "one.conllu").write_text(CONLLU, encoding="utf-8")
            with zipfile.ZipFile(corpus / "packed_TT.zip", "w") as archive:
                archive.writestr("packed_TT/one.tt", TT)

            report = self.audit.audit_upstream(root)

        self.assertEqual(report["paired_document_count"], 1)
        self.assertEqual(report["compared_document_count"], 1)
        self.assertEqual(report["tt_packaging"], {"archive": 1})
        self.assertEqual(report["field_mismatch_counts"]["norm"], 0)
        self.assertEqual(report["field_mismatch_counts"]["head"], 0)

    def test_whitespace_only_conllu_counterpart_is_a_placeholder_not_token_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "aggregate" / "aggregate_TT"
            conllu_dir = root / "aggregate" / "aggregate_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)
            (tt_dir / "one.tt").write_text(TT, encoding="utf-8")
            (conllu_dir / "one.conllu").write_text("\n", encoding="utf-8")

            report = self.audit.audit_upstream(root)

        self.assertEqual(report["paired_document_count"], 1)
        self.assertEqual(report["compared_document_count"], 0)
        self.assertEqual(report["conllu_placeholder_count"], 1)
        self.assertEqual(
            report["conllu_placeholders"],
            [
                {
                    "dataset": "aggregate/aggregate",
                    "record": "one",
                    "source": "aggregate/aggregate_CONLLU/one.conllu",
                }
            ],
        )
        self.assertEqual(report["token_count_mismatches"], [])
        self.assertEqual(report["compared_tokens"], 0)

    def test_reports_token_and_shared_field_mismatches_without_resolving_them(self):
        mismatching = '''# newdoc id = demo:one
1	ⲁ	DIFFERENT	VERB	V	_	0	root	_	_
2	X	ⲃ	NOUN	WRONG	_	1	obl	_	_
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "demo" / "demo_TT"
            conllu_dir = root / "demo" / "demo_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)
            (tt_dir / "one.tt").write_text(TT, encoding="utf-8")
            (conllu_dir / "one.conllu").write_text(mismatching, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["token_count_mismatches"], [])
        self.assertEqual(report["compared_document_count"], 1)
        self.assertEqual(
            report["field_mismatch_counts"],
            {"func": 1, "head": 0, "lemma": 1, "norm": 1, "pos": 1},
        )
        examples = {
            (item["field"], item["token_index"])
            for item in report["field_mismatch_examples"]
        }
        self.assertEqual(
            examples, {("lemma", 1), ("norm", 2), ("pos", 2), ("func", 2)}
        )

    def test_reports_unpaired_and_token_count_mismatch_documents(self):
        short_conllu = "1\tⲁ\tⲁ\tVERB\tV\t_\t0\troot\t_\t_\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "demo" / "demo_TT"
            conllu_dir = root / "demo" / "demo_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)
            (tt_dir / "paired.tt").write_text(TT, encoding="utf-8")
            (tt_dir / "tt-only.tt").write_text(TT, encoding="utf-8")
            (conllu_dir / "paired.conllu").write_text(short_conllu, encoding="utf-8")
            (conllu_dir / "conllu-only.conllu").write_text(CONLLU, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["paired_document_count"], 1)
        self.assertEqual(report["compared_document_count"], 0)
        self.assertEqual(report["tt_only"], ["demo/demo:tt-only"])
        self.assertEqual(report["conllu_only"], ["demo/demo:conllu-only"])
        self.assertEqual(
            report["token_count_mismatches"],
            [
                {
                    "dataset": "demo/demo",
                    "record": "paired",
                    "tt_tokens": 2,
                    "conllu_tokens": 1,
                }
            ],
        )

    def test_casefold_collision_in_one_representation_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "demo" / "demo_TT"
            conllu_dir = root / "demo" / "demo_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)
            (tt_dir / "A.tt").write_text(TT, encoding="utf-8")
            (tt_dir / "a.tt").write_text(TT, encoding="utf-8")
            (conllu_dir / "a.conllu").write_text(CONLLU, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "case-insensitive.*collision"):
                self.audit.audit_upstream(root)


if __name__ == "__main__":
    unittest.main()
