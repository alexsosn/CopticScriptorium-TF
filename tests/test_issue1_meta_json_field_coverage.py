import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "meta_json_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_meta_json_coverage", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load meta.json audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MetaJsonFieldCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_reports_fields_present_on_only_one_side_without_merging_them(self):
        tt = (
            '<meta corpus="demo" document_cts_urn="urn:cts:demo:one" '
            'title="One" tt_only="source-value">\n'
            '<norm xml:id="u1" func="root" norm="x">x</norm>\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "demo" / "demo_TT"
            direct.mkdir(parents=True)
            (direct / "one.tt").write_text(tt, encoding="utf-8")
            (root / "meta.json").write_text(
                json.dumps(
                    {
                        "one": {
                            "title": "One",
                            "license": "CC-BY 4.0",
                            "global_only": "index-value",
                        }
                    }
                ),
                encoding="utf-8",
            )

            report = self.audit.audit_upstream(root)

        reconciliation = report["meta_json"]["reconciliation"]
        self.assertEqual(
            reconciliation["meta_fields_missing_in_tt_counts"],
            {"global_only": 1, "license": 1},
        )
        self.assertEqual(
            reconciliation["tt_fields_missing_in_meta_counts"],
            {"corpus": 1, "document_cts_urn": 1, "tt_only": 1},
        )
        self.assertEqual(
            reconciliation["meta_fields_missing_in_tt_examples"],
            [
                {
                    "record": "one",
                    "source": "demo/demo_TT/one.tt",
                    "field": "global_only",
                    "meta_json": "index-value",
                },
                {
                    "record": "one",
                    "source": "demo/demo_TT/one.tt",
                    "field": "license",
                    "meta_json": "CC-BY 4.0",
                },
            ],
        )
        self.assertEqual(
            reconciliation["tt_fields_missing_in_meta_examples"],
            [
                {
                    "record": "one",
                    "source": "demo/demo_TT/one.tt",
                    "field": "corpus",
                    "tt": "demo",
                },
                {
                    "record": "one",
                    "source": "demo/demo_TT/one.tt",
                    "field": "document_cts_urn",
                    "tt": "urn:cts:demo:one",
                },
                {
                    "record": "one",
                    "source": "demo/demo_TT/one.tt",
                    "field": "tt_only",
                    "tt": "source-value",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
