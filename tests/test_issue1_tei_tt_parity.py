import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "tei_tt_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_tei_tt", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load TEI-TT audit from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TT = '''<meta document_cts_urn="urn:cts:copticLit:demo.work.ms" license="CC-BY 4.0">
<translation translation="English translation">
<pb n="1"><cb n="1"><lb n="1"><norm xml:id="u1" norm="ⲣⲱⲙⲉ" lemma="ⲣⲱⲙⲉ" pos="N">
'''

TT_NO_TRANSLATION = '''<meta document_cts_urn="urn:cts:copticLit:demo.work.ms" license="CC-BY 4.0">
<pb n="1"><cb n="1"><lb n="1"><norm xml:id="u1" norm="ⲣⲱⲙⲉ" lemma="ⲣⲱⲙⲉ" pos="N">
'''

TEI = '''<TEI xmlns="http://www.tei-c.org/ns/1.0">
<teiHeader><fileDesc><titleStmt><title ref="urn:cts:copticLit:demo.work.ms">Demo</title></titleStmt><publicationStmt><availability><licence>CC-BY 4.0</licence></availability></publicationStmt></fileDesc></teiHeader>
<text><body><pb n="1"/><cb n="1"/><p><s style="English translation"><lb n="1"/><w type="N" lemma="ⲣⲱⲙⲉ">ⲣⲱⲙⲉ</w></s></p></body></text>
</TEI>'''


class TeiTtParityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def _write_direct(self, root: Path, tt_name: str, tt_text: str, tei_name: str, tei_text: str):
        tt = root / "demo" / "demo_TT"
        tei = root / "demo" / "demo_TEI"
        tt.mkdir(parents=True, exist_ok=True)
        tei.mkdir(parents=True, exist_ok=True)
        (tt / tt_name).write_text(tt_text, encoding="utf-8")
        (tei / tei_name).write_text(tei_text, encoding="utf-8")

    def test_pairs_case_insensitively_and_compares_layer_presence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_direct(root, "Doc.tt", TT, "doc.xml", TEI)
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["paired_document_count"], 1)
        self.assertEqual(report["case_variant_count"], 1)
        self.assertEqual(report["tei_only_records"], [])
        self.assertEqual(report["tt_only_records_in_tei_datasets"], [])
        self.assertEqual(
            report["tei_only_layer_presence"],
            {"column": 0, "cts": 0, "lemma": 0, "license": 0, "line": 0, "page": 0, "pos": 0, "translation": 0},
        )
        self.assertEqual(report["errors"], [])

    def test_surfaces_tei_layer_presence_missing_from_tt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_direct(root, "doc.tt", TT_NO_TRANSLATION, "doc.xml", TEI)
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["tei_only_layer_presence"]["translation"], 1)
        self.assertEqual(report["tei_only_examples"][0]["layer"], "translation")
        self.assertEqual(report["tei_only_examples"][0]["record"], "doc")

    def test_reads_tt_archive_counterpart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "demo"
            corpus.mkdir()
            with zipfile.ZipFile(corpus / "demo_TT.zip", "w") as archive:
                archive.writestr("demo_TT/doc.tt", TT)
            tei = corpus / "demo_TEI"
            tei.mkdir()
            (tei / "doc.xml").write_text(TEI, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["paired_document_count"], 1)
        self.assertEqual(report["tt_packaging"], {"archive": 1})

    def test_tt_dataset_without_tei_is_classified_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt = root / "no-tei" / "no.tei_TT"
            tt.mkdir(parents=True)
            (tt / "doc.tt").write_text(TT, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["tei_dataset_count"], 0)
        self.assertEqual(report["tt_datasets_without_tei"], ["no-tei/no.tei"])
        self.assertEqual(report["tt_only_records_in_tei_datasets"], [])


if __name__ == "__main__":
    unittest.main()
