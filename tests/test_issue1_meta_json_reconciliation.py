import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "semantic_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_semantic_audit_meta", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load semantic audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tt(title: str) -> str:
    return (
        f'<meta corpus="demo" document_cts_urn="urn:cts:demo:one" '
        f'license="CC" title="{title}">\n'
        '<norm xml:id="u1" func="root" norm="x">x</norm>\n'
    )


class MetaJsonReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_reconciles_global_meta_json_to_multiple_tt_copies_and_measures_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "source-a" / "demo_TT"
            second = root / "source-b" / "demo_TT"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "one.tt").write_text(tt("One"), encoding="utf-8")
            (second / "one.tt").write_text(tt("Alternate title"), encoding="utf-8")
            (root / "meta.json").write_text(
                json.dumps({"one": {"title": "One", "license": "CC"}, "orphan": {"title": "Orphan"}}),
                encoding="utf-8",
            )

            report = self.audit.audit_upstream(root)

        reconciliation = report["meta_json"]["reconciliation"]
        self.assertEqual(reconciliation["matched_tt_document_count"], 2)
        self.assertEqual(reconciliation["tt_without_meta_json"], [])
        self.assertEqual(reconciliation["meta_json_without_tt"], ["orphan"])
        self.assertEqual(reconciliation["record_copy_counts"], {"one": 2})
        self.assertEqual(reconciliation["field_mismatch_counts"], {"title": 1})
        self.assertEqual(
            reconciliation["field_mismatch_examples"],
            [
                {
                    "record": "one",
                    "source": "source-b/demo_TT/one.tt",
                    "field": "title",
                    "tt": "Alternate title",
                    "meta_json": "One",
                }
            ],
        )

    def test_casefold_collision_in_meta_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "demo" / "demo_TT"
            direct.mkdir(parents=True)
            (direct / "one.tt").write_text(tt("One"), encoding="utf-8")
            (root / "meta.json").write_text(
                json.dumps({"ONE": {"title": "One"}, "one": {"title": "One"}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "meta.json.*case-insensitive.*collision"):
                self.audit.audit_upstream(root)


if __name__ == "__main__":
    unittest.main()
