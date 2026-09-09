import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "annis_meta_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_annis_meta", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load relANNIS metadata audit from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CORPUS = """1\tone\tDOCUMENT\tNULL\t1\t2\tFALSE
2\ttwo\tDOCUMENT\tNULL\t3\t4\tFALSE
3\tdemo\tCORPUS\tNULL\t0\t5\tTRUE
"""
ANNOTATIONS = """1\tNULL\ttitle\tOne
1\tNULL\tlicense\t<a href='x'>CC</a>
2\tNULL\ttitle\tTwo
2\tNULL\textra\tANNIS only
2\tNULL\tescaped\tLine\\tTabbed\\\\Tail
3\tNULL\tdescription\tDataset description
"""


class AnnisMetaAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_reconciles_document_annotations_and_keeps_corpus_metadata_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            annis = root / "demo" / "demo_ANNIS"
            annis.mkdir(parents=True)
            (annis / "corpus.annis").write_text(CORPUS, encoding="utf-8")
            (annis / "corpus_annotation.annis").write_text(ANNOTATIONS, encoding="utf-8")
            (root / "meta.json").write_text(
                json.dumps(
                    {
                        "one": {"title": "One", "license": "CC", "meta_only": "M"},
                        "two": {"title": "Two", "escaped": "Line\tTabbed\\Tail"},
                    }
                ),
                encoding="utf-8",
            )

            report = self.audit.audit_upstream(root)

        self.assertEqual(report["dataset_count"], 1)
        self.assertEqual(report["document_count"], 2)
        self.assertEqual(report["corpus_node_count"], 1)
        self.assertEqual(report["matched_document_count"], 2)
        self.assertEqual(report["annis_documents_without_meta_json"], [])
        self.assertEqual(report["meta_json_without_annis_document"], [])
        self.assertEqual(report["document_field_mismatch_counts"], {"license": 1})
        self.assertEqual(report["annis_fields_missing_in_meta_counts"], {"extra": 1})
        self.assertEqual(report["meta_fields_missing_in_annis_counts"], {"meta_only": 1})
        self.assertEqual(report["corpus_annotation_key_occurrences"], {"description": 1})
        self.assertEqual(
            report["document_field_mismatch_examples"],
            [
                {
                    "dataset": "demo/demo",
                    "record": "one",
                    "field": "license",
                    "annis": "<a href='x'>CC</a>",
                    "meta_json": "CC",
                }
            ],
        )

    def test_reads_archive_packaged_annis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "packed"
            corpus.mkdir()
            with zipfile.ZipFile(corpus / "packed_ANNIS.zip", "w") as archive:
                archive.writestr("packed_ANNIS/corpus.annis", CORPUS)
                archive.writestr("packed_ANNIS/corpus_annotation.annis", ANNOTATIONS)
            (root / "meta.json").write_text(
                json.dumps(
                    {
                        "one": {"title": "One"},
                        "two": {"title": "Two", "escaped": "Line\tTabbed\\Tail"},
                    }
                ),
                encoding="utf-8",
            )

            report = self.audit.audit_upstream(root)

        self.assertEqual(report["dataset_count"], 1)
        self.assertEqual(report["packaging"], {"archive": 1})
        self.assertEqual(report["document_count"], 2)
        self.assertEqual(report["corpus_node_count"], 1)

    def test_reads_legacy_relannis_tab_archive_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "legacy"
            corpus.mkdir()
            with zipfile.ZipFile(corpus / "legacy_ANNIS.zip", "w") as archive:
                archive.writestr("legacy/corpus.tab", CORPUS)
                archive.writestr("legacy/corpus_annotation.tab", ANNOTATIONS)
            (root / "meta.json").write_text(
                json.dumps(
                    {
                        "one": {"title": "One"},
                        "two": {"title": "Two", "escaped": "Line\tTabbed\\Tail"},
                    }
                ),
                encoding="utf-8",
            )

            report = self.audit.audit_upstream(root)

        self.assertEqual(report["dataset_count"], 1)
        self.assertEqual(report["packaging"], {"archive": 1})
        self.assertEqual(report["document_count"], 2)
        self.assertEqual(report["corpus_node_count"], 1)

    def test_casefold_collision_in_annis_document_names_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            annis = root / "demo" / "demo_ANNIS"
            annis.mkdir(parents=True)
            (annis / "corpus.annis").write_text(
                "1\tOne\tDOCUMENT\tNULL\t1\t2\tFALSE\n2\tone\tDOCUMENT\tNULL\t3\t4\tFALSE\n",
                encoding="utf-8",
            )
            (annis / "corpus_annotation.annis").write_text("", encoding="utf-8")
            (root / "meta.json").write_text(json.dumps({"one": {}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "relANNIS.*case-insensitive.*collision"):
                self.audit.audit_upstream(root)


if __name__ == "__main__":
    unittest.main()
