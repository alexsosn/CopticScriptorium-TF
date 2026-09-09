import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ISSUE_DIR = ROOT / "research" / "issue-1"


def load_module(name: str, filename: str):
    path = ISSUE_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load research module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SourceEncodingIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conllu_sources = load_module("issue1_encoding_conllu_sources", "conllu_sources.py")
        cls.tt_audits = (
            load_module("issue1_encoding_semantic", "semantic_audit.py"),
            load_module("issue1_encoding_cross", "cross_format_audit.py"),
            load_module("issue1_encoding_meta_json", "meta_json_audit.py"),
            load_module("issue1_encoding_tei_tt", "tei_tt_audit.py"),
        )

    def test_directory_conllu_invalid_utf8_is_not_replacement_decoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "demo" / "demo_CONLLU"
            directory.mkdir(parents=True)
            (directory / "one.conllu").write_bytes(
                b"1\tbad\xff\tbad\tNOUN\tN\t_\t0\troot\t_\t_\n"
            )
            with self.assertRaises(UnicodeDecodeError):
                list(self.conllu_sources.iter_conllu_records(root))

    def test_archive_conllu_invalid_utf8_is_not_replacement_decoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "demo"
            corpus.mkdir()
            with zipfile.ZipFile(corpus / "demo_CONLLU.zip", "w") as archive:
                archive.writestr(
                    "one.conllu",
                    b"1\tbad\xff\tbad\tNOUN\tN\t_\t0\troot\t_\t_\n",
                )
            with self.assertRaises(UnicodeDecodeError):
                list(self.conllu_sources.iter_conllu_records(root))

    def test_directory_tt_invalid_utf8_fails_all_tt_audits(self):
        invalid = b'<meta corpus="demo" title="bad\xff">\n'
        for index, audit in enumerate(self.tt_audits):
            with self.subTest(audit=audit.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                directory = root / "demo" / "demo_TT"
                directory.mkdir(parents=True)
                (directory / "one.tt").write_bytes(invalid)
                (root / "meta.json").write_text(json.dumps({}), encoding="utf-8")
                with self.assertRaises(UnicodeDecodeError):
                    audit.audit_upstream(root)

    def test_archive_tt_invalid_utf8_fails_all_tt_audits(self):
        invalid = b'<meta corpus="demo" title="bad\xff">\n'
        for audit in self.tt_audits:
            with self.subTest(audit=audit.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                corpus = root / "demo"
                corpus.mkdir()
                with zipfile.ZipFile(corpus / "demo_TT.zip", "w") as archive:
                    archive.writestr("one.tt", invalid)
                (root / "meta.json").write_text(json.dumps({}), encoding="utf-8")
                with self.assertRaises(UnicodeDecodeError):
                    audit.audit_upstream(root)


if __name__ == "__main__":
    unittest.main()
