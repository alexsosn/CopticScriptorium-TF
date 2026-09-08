import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "inventory.py"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "issue1_tree_sample.json"


def load_inventory_module():
    spec = importlib.util.spec_from_file_location("issue1_inventory", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load inventory module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InventoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = load_inventory_module()
        cls.payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_classifies_only_known_format_directories(self):
        classify = self.inventory.classify_format_directory
        self.assertEqual(
            classify("AP/apophthegmata.patrum_TT"),
            ("AP", "apophthegmata.patrum", "TT"),
        )
        self.assertEqual(
            classify("AP/apophthegmata.patrum_CONLLU"),
            ("AP", "apophthegmata.patrum", "CONLLU"),
        )
        self.assertEqual(
            classify("AP/apophthegmata.patrum_TEI"),
            ("AP", "apophthegmata.patrum", "TEI"),
        )
        self.assertEqual(
            classify("AP/apophthegmata.patrum_PAULA"),
            ("AP", "apophthegmata.patrum", "PAULA"),
        )
        self.assertEqual(
            classify("AP/apophthegmata.patrum_ANNIS"),
            ("AP", "apophthegmata.patrum", "ANNIS"),
        )
        self.assertIsNone(classify("AP/README.md"))
        self.assertIsNone(classify("AP/not_a_format_suffix"))
        self.assertIsNone(classify("too/deep/name_TT/child"))

    def test_rejects_truncated_recursive_tree(self):
        payload = dict(self.payload)
        payload["truncated"] = True
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.inventory.analyze_tree(payload)

    def test_reports_format_presence_without_treating_paula_or_annis_as_record_stems(self):
        report = self.inventory.analyze_tree(self.payload)
        dataset = report["datasets"]["AP/apophthegmata.patrum"]
        self.assertEqual(
            dataset["formats"],
            ["ANNIS", "CONLLU", "PAULA", "TEI", "TT"],
        )
        self.assertEqual(
            dataset["records"]["AP.004.poemen.65"],
            {
                "CONLLU": "AP/apophthegmata.patrum_CONLLU/AP.004.poemen.65.conllu",
                "TEI": "AP/apophthegmata.patrum_TEI/AP.004.poemen.65.xml",
                "TT": "AP/apophthegmata.patrum_TT/AP.004.poemen.65.tt",
            },
        )
        self.assertNotIn("PAULA", dataset["records"]["AP.004.poemen.65"])
        self.assertNotIn("ANNIS", dataset["records"]["AP.004.poemen.65"])

    def test_reports_asymmetric_record_counterparts(self):
        report = self.inventory.analyze_tree(self.payload)
        dataset = report["datasets"]["AP/apophthegmata.patrum"]
        self.assertEqual(
            dataset["missing_counterparts"],
            {
                "AP.empty": ["CONLLU", "TEI"],
                "AP.only-conllu": ["TEI", "TT"],
            },
        )

    def test_reports_zero_byte_blobs_with_identity(self):
        report = self.inventory.analyze_tree(self.payload)
        self.assertEqual(
            report["zero_byte_blobs"],
            [
                {
                    "path": "AP/apophthegmata.patrum_TT/AP.empty.tt",
                    "sha": "tt-empty",
                }
            ],
        )

    def test_records_meta_json_blob_identity(self):
        report = self.inventory.analyze_tree(self.payload)
        self.assertEqual(
            report["meta_json"],
            {
                "path": "meta.json",
                "sha": "meta-sha",
                "size": 2461846,
            },
        )

    def test_report_order_is_deterministic_even_if_tree_entries_are_reversed(self):
        forward = self.inventory.analyze_tree(self.payload)
        reversed_payload = dict(self.payload)
        reversed_payload["tree"] = list(reversed(self.payload["tree"]))
        backward = self.inventory.analyze_tree(reversed_payload)
        self.assertEqual(forward, backward)
        self.assertEqual(
            self.inventory.render_report_json(forward),
            self.inventory.render_report_json(backward),
        )


if __name__ == "__main__":
    unittest.main()
