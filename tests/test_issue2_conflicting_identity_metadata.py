import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "identity_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_identity_conflict", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load identity audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_meta(root: Path, record: str, meta_attributes: str) -> None:
    directory = root / "demo" / "demo_TT"
    directory.mkdir(parents=True, exist_ok=True)
    text = (
        f"<meta corpus=\"demo\" {meta_attributes} redundant=\"no\">\n"
        '<orig orig="Ⲁ">\n'
        '<norm xml:id="u1" func="root" pos="N" lemma="ⲁ" norm="ⲁ">Ⲁ</norm>\n'
        "</orig>\n"
    )
    (directory / f"{record}.tt").write_text(text, encoding="utf-8")


class ConflictingIdentityMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_equal_duplicate_cts_is_ledgered_but_identity_remains_usable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cts = "urn:cts:demo:one"
            write_meta(
                root,
                "one",
                f'document_cts_urn="{cts}" document_cts_urn="{cts}"',
            )
            report = self.audit.audit_upstream(root)
            self.assertEqual(report["scholarly_identity_count"], 1)
            self.assertEqual(report["records"][0]["scholarly_id"], cts)
            self.assertEqual(len(report["duplicate_meta_attribute_records"]), 1)
            self.assertEqual(report["identity_conflict_records"], [])

    def test_conflicting_duplicate_cts_is_not_resolved_by_first_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_meta(
                root,
                "bad",
                'document_cts_urn="urn:cts:demo:first" '
                'document_cts_urn="urn:cts:demo:second"',
            )
            report = self.audit.audit_upstream(root)
            self.assertEqual(report["scholarly_identity_count"], 0)
            self.assertIsNone(report["records"][0]["scholarly_id"])
            self.assertEqual(len(report["identity_conflict_records"]), 1)
            conflict = report["identity_conflict_records"][0]
            self.assertEqual(
                conflict["values"],
                ["urn:cts:demo:first", "urn:cts:demo:second"],
            )
            self.assertEqual(
                report["missing_scholarly_identity_records"][0]["identity_status"],
                "conflicting_document_cts_urn",
            )


if __name__ == "__main__":
    unittest.main()
