import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "tei_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_tei", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load TEI audit from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TEI = '''<TEI xmlns="http://www.tei-c.org/ns/1.0">
<teiHeader>
  <fileDesc>
    <titleStmt><title ref="urn:cts:copticLit:demo.work.ms">Demo</title></titleStmt>
    <publicationStmt><availability><licence target="https://creativecommons.org/licenses/by/4.0/">CC-BY 4.0</licence></availability></publicationStmt>
    <sourceDesc><msDesc><msIdentifier><repository>Demo Library</repository></msIdentifier></msDesc></sourceDesc>
  </fileDesc>
  <profileDesc><langUsage><language ident="cop">Sahidic Coptic</language></langUsage></profileDesc>
</teiHeader>
<text><body><div1><pb xml:id="p1"/><cb n="1"/><p><s style="English translation"><lb n="1"/><phr><w type="N" lemma="ⲣⲱⲙⲉ">ⲣⲱ<lb n="2"/>ⲙⲉ<m>ⲣⲱⲙⲉ</m></w></phr></s></p></div1></body></text>
</TEI>'''


class TeiAuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def _write(self, root: Path, corpus: str, dataset: str, name: str, text: str):
        directory = root / corpus / f"{dataset}_TEI"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_inventories_structural_and_metadata_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "demo", "demo", "Doc.XML", TEI)
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["dataset_count"], 1)
        self.assertEqual(report["document_count"], 1)
        self.assertEqual(report["datasets"], ["demo/demo"])
        self.assertEqual(report["root_element_counts"], {"TEI": 1})
        self.assertEqual(report["documents_with_tei_header"], 1)
        self.assertEqual(report["documents_with_cts_ref"], 1)
        self.assertEqual(report["documents_with_license"], 1)
        self.assertEqual(report["documents_with_language_usage"], 1)
        self.assertEqual(report["documents_with_repository"], 1)
        self.assertEqual(report["documents_with_sentence_translation"], 1)
        self.assertEqual(report["documents_with_words"], 1)
        self.assertEqual(report["documents_with_morphemes"], 1)
        self.assertEqual(report["documents_with_page_breaks"], 1)
        self.assertEqual(report["documents_with_column_breaks"], 1)
        self.assertEqual(report["documents_with_line_breaks"], 1)
        self.assertEqual(report["words_split_by_layout"], 1)
        self.assertEqual(report["errors"], [])

    def test_casefold_identity_collisions_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "demo", "demo", "Doc.xml", TEI)
            self._write(root, "demo", "demo", "doc.xml", TEI)
            with self.assertRaisesRegex(ValueError, "case-insensitive TEI record collision"):
                self.audit.audit_upstream(root)

    def test_malformed_xml_is_reported_with_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "bad", "bad", "broken.xml", "<TEI><broken>")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["document_count"], 1)
        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(report["errors"][0]["kind"], "malformed_xml")
        self.assertEqual(report["errors"][0]["source"], "bad/bad_TEI/broken.xml")

    def test_report_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "z", "z", "z.xml", TEI)
            self._write(root, "a", "a", "a.xml", TEI)
            first = self.audit.audit_upstream(root)
            second = self.audit.audit_upstream(root)

        self.assertEqual(first, second)
        self.assertEqual(self.audit.render_report_json(first), self.audit.render_report_json(second))


if __name__ == "__main__":
    unittest.main()
