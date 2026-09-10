import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "identity_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_identity_audit_orig", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load identity audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tt(root: Path, corpus: str, orig: str) -> None:
    directory = root / corpus / f"{corpus}_TT"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "one.tt").write_text(
        '<meta corpus="demo" document_cts_urn="urn:cts:demo:one" parsing="gold">\n'
        f'<orig orig="{orig}">\n'
        '<norm xml:id="u1" func="root" pos="N" lemma="ⲁ" norm="ⲁ">\n'
        f'{orig}\n'
        '</norm>\n</orig>\n',
        encoding="utf-8",
    )


class OriginalTextIdentityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_same_normalized_text_but_different_original_is_textual_divergence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(root, "a", "Ⲁ")
            write_tt(root, "b", "Ⲃ")
            group = cls_report = self.audit.audit_upstream(root)["duplicate_scholarly_identities"][0]
            self.assertEqual(cls_report["classification"], "textual_divergence")
            self.assertEqual(len({r["normalized_text_sha256"] for r in group["records"]}), 1)
            self.assertEqual(len({r["original_text_sha256"] for r in group["records"]}), 2)


if __name__ == "__main__":
    unittest.main()
