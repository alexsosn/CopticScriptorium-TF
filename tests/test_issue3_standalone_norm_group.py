import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_shape_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_graph_shape_standalone", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph shape audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def standalone_norm_group_tt() -> str:
    return (
        '<meta corpus="demo" document_cts_urn="urn:cts:demo:one" title="Demo">\n'
        '<norm_group norm_group="abc">\n'
        '<orig orig="abc">\n'
        '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="abc" norm="abc">\n'
        'abc\n'
        '</norm>\n'
        '</orig>\n'
        '</norm_group>\n'
    )


class StandaloneNormGroupContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_norm_group_without_orig_group_is_measured_not_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "demo" / "demo_TT"
            directory.mkdir(parents=True)
            (directory / "one.tt").write_text(standalone_norm_group_tt(), encoding="utf-8")

            report = self.audit.audit_upstream(root)

            self.assertEqual(report["document_count"], 1)
            self.assertEqual(report["orig_group_count"], 0)
            self.assertEqual(report["norm_group_count"], 1)
            self.assertEqual(report["group_cardinalities"]["norm_group_to_orig"], {"1": 1})
            self.assertEqual(report["norm_group_parent_contexts"], {"none": 1})


if __name__ == "__main__":
    unittest.main()
