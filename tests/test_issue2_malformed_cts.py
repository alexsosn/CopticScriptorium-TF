import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "identity_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_malformed_cts", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load identity audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tt(root: Path, cts: str) -> None:
    directory = root / "demo" / "demo_TT"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "one.tt").write_text(
        f'<meta corpus="demo" document_cts_urn="{cts}" redundant="no" parsing="gold">\n'
        '<orig orig="Ⲁ">\n'
        '<norm xml:id="u1" func="root" pos="N" lemma="ⲁ" norm="ⲁ">Ⲁ</norm>\n'
        '</orig>\n',
        encoding="utf-8",
    )


class MalformedScholarlyIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_non_cts_document_identity_is_ledgered_not_grouped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(root, "not-a-cts-urn")

            report = self.audit.audit_upstream(root)
            self.assertEqual(report["scholarly_identity_count"], 0)
            self.assertIsNone(report["records"][0]["scholarly_id"])
            self.assertEqual(
                report["records"][0]["identity_status"],
                "malformed_document_cts_urn",
            )
            self.assertEqual(len(report["malformed_scholarly_identity_records"]), 1)
            malformed = report["malformed_scholarly_identity_records"][0]
            self.assertEqual(malformed["value"], "not-a-cts-urn")
            self.assertEqual(
                report["missing_scholarly_identity_records"][0]["identity_status"],
                "malformed_document_cts_urn",
            )

    def test_cts_identity_with_whitespace_is_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(root, "urn:cts:demo:bad value")
            report = self.audit.audit_upstream(root)
            self.assertEqual(report["scholarly_identity_count"], 0)
            self.assertEqual(len(report["malformed_scholarly_identity_records"]), 1)


if __name__ == "__main__":
    unittest.main()
