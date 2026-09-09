import importlib.util
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "paula_audit.py"
TEXT_XML = '<paula version="1.1"><header paula_id="doc.text"/><body>abc</body></paula>'


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_paula_mixed", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load PAULA audit from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PaulaMixedWrapperContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_direct_xml_plus_inner_paula_zip_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus_dir = root / "mixed"
            corpus_dir.mkdir(parents=True)
            inner = BytesIO()
            with zipfile.ZipFile(inner, "w") as archive:
                archive.writestr("mixed/inner.text.xml", TEXT_XML)
            outer_path = corpus_dir / "mixed_PAULA.zip"
            with zipfile.ZipFile(outer_path, "w") as archive:
                archive.writestr("direct.text.xml", TEXT_XML)
                archive.writestr("mixed_PAULA.zip", inner.getvalue())

            with self.assertRaisesRegex(ValueError, "mixed PAULA archive"):
                self.audit.audit_upstream(root)


if __name__ == "__main__":
    unittest.main()
