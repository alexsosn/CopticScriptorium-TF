import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_shape_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_graph_meta_duplicates", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph shape audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GraphShapeMetadataDuplicateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_duplicate_meta_attributes_do_not_block_graph_shape_measurement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "demo" / "demo_TT"
            directory.mkdir(parents=True)
            (directory / "one.tt").write_text(
                '<meta corpus="demo" people="A" people="B">\n'
                '<orig_group orig_group="a">\n'
                '<norm_group norm_group="a">\n'
                '<orig orig="a">\n'
                '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a</norm>\n'
                '</orig>\n'
                '</norm_group>\n'
                '</orig_group>\n',
                encoding="utf-8",
            )
            report = self.audit.audit_upstream(root)
            self.assertEqual(report["document_count"], 1)
            self.assertEqual(report["norm_token_count"], 1)


if __name__ == "__main__":
    unittest.main()
