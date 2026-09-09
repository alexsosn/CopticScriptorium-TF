import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "fetch_inventory.py"


def load_transport_module():
    spec = importlib.util.spec_from_file_location("issue1_inventory_transport", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load transport module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CompleteTreeTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transport = load_transport_module()

    def test_assembles_root_files_and_prefixed_recursive_subtrees(self):
        root = {
            "sha": "root-tree",
            "truncated": False,
            "tree": [
                {"path": "AP", "type": "tree", "sha": "ap-tree", "mode": "040000"},
                {"path": "README.md", "type": "blob", "sha": "readme", "mode": "100644", "size": 10},
                {"path": "meta.json", "type": "blob", "sha": "meta", "mode": "100644", "size": 20},
            ],
        }
        subtrees = {
            "AP": {
                "sha": "ap-tree",
                "truncated": False,
                "tree": [
                    {"path": "dataset_TT", "type": "tree", "sha": "tt-tree", "mode": "040000"},
                    {"path": "dataset_TT/a.tt", "type": "blob", "sha": "a", "mode": "100644", "size": 3},
                ],
            }
        }
        combined = self.transport.assemble_complete_tree(root, subtrees)
        self.assertFalse(combined["truncated"])
        self.assertEqual(combined["sha"], "root-tree")
        self.assertEqual(
            [entry["path"] for entry in combined["tree"]],
            [
                "AP",
                "AP/dataset_TT",
                "AP/dataset_TT/a.tt",
                "README.md",
                "meta.json",
            ],
        )

    def test_rejects_truncated_root_or_subtree(self):
        root = {"sha": "root", "truncated": True, "tree": []}
        with self.assertRaisesRegex(ValueError, "root.*truncated"):
            self.transport.assemble_complete_tree(root, {})

        root = {
            "sha": "root",
            "truncated": False,
            "tree": [{"path": "AP", "type": "tree", "sha": "ap", "mode": "040000"}],
        }
        with self.assertRaisesRegex(ValueError, "AP.*truncated"):
            self.transport.assemble_complete_tree(
                root,
                {"AP": {"sha": "ap", "truncated": True, "tree": []}},
            )

    def test_requires_one_subtree_payload_per_top_level_tree(self):
        root = {
            "sha": "root",
            "truncated": False,
            "tree": [{"path": "AP", "type": "tree", "sha": "ap", "mode": "040000"}],
        }
        with self.assertRaisesRegex(ValueError, "missing subtree.*AP"):
            self.transport.assemble_complete_tree(root, {})

    def test_collect_complete_tree_uses_nonrecursive_root_and_recursive_top_level_subtrees(self):
        calls = []
        responses = {
            "/repos/CopticScriptorium/corpora/git/commits/pinned": {
                "tree": {"sha": "root-tree"}
            },
            "/repos/CopticScriptorium/corpora/git/trees/root-tree": {
                "sha": "root-tree",
                "truncated": False,
                "tree": [
                    {"path": "AP", "type": "tree", "sha": "ap-tree", "mode": "040000"},
                    {"path": "meta.json", "type": "blob", "sha": "meta", "mode": "100644", "size": 20},
                ],
            },
            "/repos/CopticScriptorium/corpora/git/trees/ap-tree?recursive=1": {
                "sha": "ap-tree",
                "truncated": False,
                "tree": [
                    {"path": "dataset_TT", "type": "tree", "sha": "tt", "mode": "040000"},
                    {"path": "dataset_TT/a.tt", "type": "blob", "sha": "a", "mode": "100644", "size": 3},
                ],
            },
        }

        def fake_fetch(path):
            calls.append(path)
            return responses[path]

        result = self.transport.collect_complete_tree(
            "CopticScriptorium/corpora", "pinned", fetch_json=fake_fetch
        )
        self.assertEqual(
            calls,
            [
                "/repos/CopticScriptorium/corpora/git/commits/pinned",
                "/repos/CopticScriptorium/corpora/git/trees/root-tree",
                "/repos/CopticScriptorium/corpora/git/trees/ap-tree?recursive=1",
            ],
        )
        self.assertEqual(
            [entry["path"] for entry in result["tree"]],
            ["AP", "AP/dataset_TT", "AP/dataset_TT/a.tt", "meta.json"],
        )


if __name__ == "__main__":
    unittest.main()
