import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "tei_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_tei_root", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load TEI audit from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TeiRootValidationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def _write(self, root: Path, name: str, text: str) -> None:
        directory = root / "demo" / "demo_TEI"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(text, encoding="utf-8")

    def test_tei_local_name_without_tei_namespace_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "no-namespace.xml", "<TEI><text/></TEI>")
            report = self.audit.audit_upstream(root)

        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(report["errors"][0]["kind"], "invalid_tei_root")
        self.assertEqual(report["errors"][0]["source"], "demo/demo_TEI/no-namespace.xml")

    def test_foreign_xml_root_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "foreign.xml", '<TEI xmlns="https://example.invalid/tei"><text/></TEI>')
            report = self.audit.audit_upstream(root)

        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(report["errors"][0]["kind"], "invalid_tei_root")
        self.assertEqual(report["errors"][0]["source"], "demo/demo_TEI/foreign.xml")


if __name__ == "__main__":
    unittest.main()
