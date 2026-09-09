import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "paula_tt_metadata_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_paula_tt_metadata", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load PAULA-TT audit from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PaulaTtMetadataAuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_reconciles_document_and_corpus_metadata_scopes(self):
        paula_report = {
            "metadata_feature_instances": [
                {
                    "dataset": "demo/demo",
                    "source": "demo/demo_PAULA.zip!/demo/doc1/anno_title.xml",
                    "paula_id": "anno_title",
                    "base": "anno.xml",
                    "type": "title",
                    "values": ["One"],
                },
                {
                    "dataset": "demo/demo",
                    "source": "demo/demo_PAULA.zip!/demo/doc2/anno_title.xml",
                    "paula_id": "anno_title",
                    "base": "anno.xml",
                    "type": "title",
                    "values": ["Two"],
                },
                {
                    "dataset": "demo/demo",
                    "source": "demo/demo_PAULA.zip!/demo/doc1/anno_license.xml",
                    "paula_id": "anno_license",
                    "base": "anno.xml",
                    "type": "license",
                    "values": ["CC-BY 4.0"],
                },
                {
                    "dataset": "demo/demo",
                    "source": "demo/demo_PAULA.zip!/demo/anno_Project.xml",
                    "paula_id": "anno_Project",
                    "base": "anno.xml",
                    "type": "Project",
                    "values": ["Coptic Scriptorium"],
                },
            ]
        }
        tt_report = {"metadata_key_presence": {"title": 2, "license": 2}}

        report = self.audit.reconcile_reports(paula_report, tt_report)

        self.assertEqual(report["paula_document_record_count"], 2)
        self.assertEqual(report["document_field_counts"], {"license": 1, "title": 2})
        self.assertEqual(report["corpus_field_counts"], {"Project": 1})
        self.assertEqual(report["document_fields_only_in_paula"], [])
        self.assertEqual(report["document_fields_only_in_tt"], [])
        self.assertEqual(
            report["document_field_count_differences"],
            {"license": {"paula": 1, "tt": 2, "delta": -1}},
        )

    def test_classifies_one_level_wrapper_member_by_innermost_path(self):
        instance = {
            "dataset": "bohairic.nt/bohairic.nt",
            "source": (
                "bohairic.nt/bohairic.nt_PAULA.zip!/bohairic.nt_PAULA.zip!/"
                "bohairic.nt/40_Matthew_01/anno_license.xml"
            ),
            "type": "license",
        }
        scope, record = self.audit.classify_metadata_instance(instance)
        self.assertEqual(scope, "document")
        self.assertEqual(record, "40_Matthew_01")

    def test_corpus_member_has_no_document_record(self):
        instance = {
            "dataset": "demo/demo",
            "source": "demo/demo_PAULA.zip!/demo/anno_version_n.xml",
            "type": "version_n",
        }
        scope, record = self.audit.classify_metadata_instance(instance)
        self.assertEqual(scope, "corpus")
        self.assertIsNone(record)

    def test_ambiguous_member_layout_fails_closed(self):
        instance = {
            "dataset": "demo/demo",
            "source": "demo/demo_PAULA.zip!/wrong/doc/anno_title.xml",
            "type": "title",
        }
        with self.assertRaises(ValueError):
            self.audit.classify_metadata_instance(instance)


if __name__ == "__main__":
    unittest.main()
