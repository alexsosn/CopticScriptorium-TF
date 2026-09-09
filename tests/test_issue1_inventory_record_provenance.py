import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "inventory.py"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "issue1_tree_sample.json"


def load_inventory_module():
    spec = importlib.util.spec_from_file_location("issue1_inventory_record_provenance", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load inventory module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InventoryRecordProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = load_inventory_module()
        cls.payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_visible_record_blobs_preserve_path_sha_and_size(self):
        report = self.inventory.analyze_tree(self.payload)
        dataset = report["datasets"]["AP/apophthegmata.patrum"]

        self.assertEqual(
            dataset["record_artifacts"]["AP.004.poemen.65"],
            {
                "CONLLU": {
                    "path": "AP/apophthegmata.patrum_CONLLU/AP.004.poemen.65.conllu",
                    "sha": "conllu-004",
                    "size": 80,
                },
                "TEI": {
                    "path": "AP/apophthegmata.patrum_TEI/AP.004.poemen.65.xml",
                    "sha": "tei-004",
                    "size": 90,
                },
                "TT": {
                    "path": "AP/apophthegmata.patrum_TT/AP.004.poemen.65.tt",
                    "sha": "tt-004",
                    "size": 100,
                },
            },
        )

        empty = dataset["record_artifacts"]["AP.empty"]["TT"]
        self.assertEqual(empty["sha"], "tt-empty")
        self.assertEqual(empty["size"], 0)


if __name__ == "__main__":
    unittest.main()
