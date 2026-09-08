import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "inventory.py"


def load_inventory_module():
    spec = importlib.util.spec_from_file_location("issue1_inventory_casefold", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load inventory module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def payload_with(entries):
    base = [
        {"path": "AP", "type": "tree", "sha": "ap"},
        {"path": "AP/apophthegmata.patrum_TT", "type": "tree", "sha": "tt"},
        {"path": "AP/apophthegmata.patrum_CONLLU", "type": "tree", "sha": "conllu"},
        {"path": "AP/apophthegmata.patrum_TEI", "type": "tree", "sha": "tei"},
    ]
    return {"sha": "casefold-fixture", "truncated": False, "tree": base + entries}


class CaseInsensitiveRecordIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = load_inventory_module()

    def test_case_only_filename_variants_are_one_counterpart_record(self):
        report = self.inventory.analyze_tree(
            payload_with(
                [
                    {
                        "path": "AP/apophthegmata.patrum_TT/AP.001.n135.mother.tt",
                        "type": "blob",
                        "sha": "tt-record",
                        "size": 10,
                    },
                    {
                        "path": "AP/apophthegmata.patrum_CONLLU/AP.001.n135.mother.conllu",
                        "type": "blob",
                        "sha": "conllu-record",
                        "size": 10,
                    },
                    {
                        "path": "AP/apophthegmata.patrum_TEI/ap.001.n135.mother.xml",
                        "type": "blob",
                        "sha": "tei-record",
                        "size": 10,
                    },
                ]
            )
        )
        dataset = report["datasets"]["AP/apophthegmata.patrum"]
        self.assertEqual(dataset["missing_counterparts"], {})
        self.assertEqual(list(dataset["records"]), ["AP.001.n135.mother"])
        self.assertEqual(
            dataset["record_id_variants"]["AP.001.n135.mother"],
            {
                "CONLLU": "AP.001.n135.mother",
                "TEI": "ap.001.n135.mother",
                "TT": "AP.001.n135.mother",
            },
        )

    def test_casefold_collision_within_one_format_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "case-insensitive.*collision"):
            self.inventory.analyze_tree(
                payload_with(
                    [
                        {
                            "path": "AP/apophthegmata.patrum_TT/AP.same.tt",
                            "type": "blob",
                            "sha": "tt-upper",
                            "size": 10,
                        },
                        {
                            "path": "AP/apophthegmata.patrum_TT/ap.same.tt",
                            "type": "blob",
                            "sha": "tt-lower",
                            "size": 10,
                        },
                    ]
                )
            )


if __name__ == "__main__":
    unittest.main()
