import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
CONLLU_AUDIT_PATH = ROOT / "research" / "issue-1" / "conllu_audit.py"
CROSS_AUDIT_PATH = ROOT / "research" / "issue-1" / "cross_format_audit.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONLLU = '''# newdoc id = packed:one
# sent_id = packed-one_s0001
# text = ⲁ ⲃ
1\tⲁ\tⲁ\tVERB\tV\tMood=Ind\t0\troot\t_\tCxn=Demo
2\tⲃ\tⲃ\tNOUN\tN\tGender=Masc\t1\tobj\t_\t_
'''

TT = '''<meta corpus="packed" document_cts_urn="urn:cts:packed:one">
<norm xml:id="u1" func="root" pos="V" lemma="ⲁ" norm="ⲁ">ⲁ</norm>
<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="ⲃ" norm="ⲃ">ⲃ</norm>
'''


class ConlluArchivePackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conllu_audit = load_module("issue1_conllu_archive_audit", CONLLU_AUDIT_PATH)
        cls.cross_audit = load_module("issue1_cross_archive_audit", CROSS_AUDIT_PATH)

    def test_standalone_audit_reads_dataset_conllu_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "packed"
            corpus.mkdir(parents=True)
            with zipfile.ZipFile(corpus / "packed_CONLLU.zip", "w") as archive:
                archive.writestr("packed_CONLLU/one.conllu", CONLLU)

            report = self.conllu_audit.audit_upstream(root)

        self.assertEqual(report["document_count"], 1)
        self.assertEqual(report["token_rows"], 2)
        self.assertEqual(report["errors"], [])
        self.assertEqual(
            report["documents"],
            [
                {
                    "source": "packed/packed_CONLLU.zip!/packed_CONLLU/one.conllu",
                    "token_rows": 2,
                    "newdoc_ids": ["packed:one"],
                }
            ],
        )

    def test_cross_format_audit_pairs_conllu_archive_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "packed"
            tt_dir = corpus / "packed_TT"
            tt_dir.mkdir(parents=True)
            (tt_dir / "one.tt").write_text(TT, encoding="utf-8")
            with zipfile.ZipFile(corpus / "packed_CONLLU.zip", "w") as archive:
                archive.writestr("packed_CONLLU/one.conllu", CONLLU)

            report = self.cross_audit.audit_upstream(root)

        self.assertEqual(report["conllu_document_count"], 1)
        self.assertEqual(report["paired_document_count"], 1)
        self.assertEqual(report["compared_document_count"], 1)
        self.assertEqual(report["tt_only"], [])
        self.assertEqual(report["conllu_only"], [])
        self.assertEqual(report["token_count_mismatches"], [])
        self.assertEqual(report["field_mismatch_counts"]["norm"], 0)
        self.assertEqual(report["field_mismatch_counts"]["head"], 0)


if __name__ == "__main__":
    unittest.main()
