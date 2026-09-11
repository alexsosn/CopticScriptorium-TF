import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "identity_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_identity_evidence", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load identity audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tt(root: Path, *, cts: str, extra_meta: str = "") -> None:
    directory = root / "demo" / "demo_TT"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "one.tt").write_text(
        f'<meta corpus="demo" title="Demo" document_cts_urn="{cts}" '
        f'parsing="gold" {extra_meta}>\n'
        '<orig orig="Ⲁ">\n'
        '<norm xml:id="u1" func="root" pos="N" lemma="ⲁ" norm="ⲁ">Ⲁ</norm>\n'
        '</orig>\n',
        encoding="utf-8",
    )


class IdentityEvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_record_preserves_manuscript_identity_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(
                root,
                cts="urn:cts:demo:one",
                extra_meta=(
                    'collection="Pierpont Morgan Library" '
                    'repository="Morgan Library &amp; Museum" '
                    'msName="MONB.XH" idno="M.604" '
                    'Trismegistos="12345" objectType="codex" '
                    'origDate="700-799 C.E." origPlace="White Monastery" '
                    'pages_from="204" pages_to="216"'
                ),
            )

            record = self.audit.audit_upstream(root)["records"][0]
            self.assertEqual(
                record["manuscript_metadata"],
                {
                    "Trismegistos": "12345",
                    "collection": "Pierpont Morgan Library",
                    "idno": "M.604",
                    "msName": "MONB.XH",
                    "objectType": "codex",
                    "origDate": "700-799 C.E.",
                    "origPlace": "White Monastery",
                    "pages_from": "204",
                    "pages_to": "216",
                    "repository": "Morgan Library & Museum",
                },
            )

    def test_obviously_malformed_cts_shapes_are_not_grouped(self):
        malformed_values = (
            "urn:cts:demo",
            "urn:cts:demo:",
            "urn:cts::one",
            "urn:cts:demo:one,",
        )
        for cts in malformed_values:
            with self.subTest(cts=cts), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write_tt(root, cts=cts)
                report = self.audit.audit_upstream(root)
                self.assertEqual(report["scholarly_identity_count"], 0)
                self.assertEqual(report["records"][0]["identity_status"], "malformed_document_cts_urn")
                self.assertEqual(report["records"][0]["malformed_identity_value"], cts)
                self.assertEqual(len(report["malformed_scholarly_identity_records"]), 1)


if __name__ == "__main__":
    unittest.main()
