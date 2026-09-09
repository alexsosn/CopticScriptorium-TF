import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "paula_audit.py"

def load_module():
    spec = importlib.util.spec_from_file_location("issue1_paula", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load PAULA audit from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

TEXT_XML='<paula version="1.1"><header paula_id="doc.text"/><body>abc</body></paula>'
POS_XML='<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink"><header paula_id="doc.pos"/><featList type="pos" xml:base="doc.tok.xml"><feat xlink:href="#tok_1" value="N"/></featList></paula>'
META_XML='<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink"><header paula_id="demo.meta_license"/><featList type="license" xml:base="demo.anno.xml"><feat xlink:href="#anno_1" value="CC-BY 4.0"/></featList></paula>'
PEPPER_META_XML='<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink"><header paula_id="demo.meta_author"/><featList type="author" xml:base="meta"><feat xlink:href="#anno_1" value="Demo Author"/></featList></paula>'
ANNOFEAT_XML='<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink"><header paula_id="demo.annoFeat"/><featList type="annoFeat" xml:base="demo.anno.xml"><feat xlink:href="#rel_1" value="tok"/></featList></paula>'
MULTI_META_XML='<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink"><header paula_id="demo.meta_multiFeat"/><multiFeatList type="multiFeat" xml:base="demo.anno.xml"><multiFeat xlink:href="#anno_1"><feat name="language" value="Coptic"/><feat name="source_format" value="PAULA XML"/></multiFeat></multiFeatList></paula>'

class PaulaAuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.audit=load_module()
    def _write_archive(self, root, corpus, dataset, members, nested=False):
        corpus_dir=root/corpus; corpus_dir.mkdir(parents=True,exist_ok=True)
        if nested:
            package_dir=corpus_dir/f"{dataset}_PAULA"; package_dir.mkdir(); archive_path=package_dir/f"{dataset}_PAULA.zip"
        else: archive_path=corpus_dir/f"{dataset}_PAULA.zip"
        with zipfile.ZipFile(archive_path,"w") as a:
            for n,c in members.items(): a.writestr(n,c)
        return archive_path

    def test_metadata_and_feature_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self._write_archive(root,"demo","demo",{"doc.text.xml":TEXT_XML,"doc.pos.xml":POS_XML,"demo.meta_license.xml":META_XML,"demo.meta_author.xml":PEPPER_META_XML})
            report=self.audit.audit_upstream(root)
        self.assertEqual(report["metadata_feature_type_occurrences"],{"author":1,"license":1})
        self.assertEqual(report["feature_type_examples"]["license"][0]["base"],"demo.anno.xml")
        self.assertEqual(report["feature_type_examples"]["author"][0]["base"],"meta")
        self.assertEqual(report["feature_type_examples"]["pos"][0]["base"],"doc.tok.xml")

    def test_annofeat_is_not_metadata_and_multifeat_metadata_is_expanded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self._write_archive(root,"demo","demo",{"demo.anno_feat.xml":ANNOFEAT_XML,"demo.meta_multiFeat.xml":MULTI_META_XML})
            report=self.audit.audit_upstream(root)
        self.assertEqual(report["metadata_feature_type_occurrences"],{"language":1,"source_format":1})

    def test_no_xml_package_records_member_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self._write_archive(root,"opaque","opaque",{"README.txt":"x","config.json":"{}"})
            report=self.audit.audit_upstream(root)
        self.assertEqual(report["packages_without_xml_members"],[{"dataset":"opaque/opaque","source":"opaque/opaque_PAULA.zip","members":["README.txt","config.json"]}])
        self.assertEqual(report["errors"][0]["kind"],"unsupported_package_shape")

    def test_nested_archive_packaging_is_counted_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self._write_archive(root,"nested","nested",{"nested/doc.text.xml":TEXT_XML},nested=True); report=self.audit.audit_upstream(root)
        self.assertEqual(report["source_package_count"],1); self.assertEqual(report["datasets"],["nested/nested"])

    def test_malformed_xml_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self._write_archive(root,"broken","broken",{"good.text.xml":TEXT_XML,"bad.xml":"<paula><broken>"}); report=self.audit.audit_upstream(root)
        self.assertEqual(report["errors"][0]["kind"],"malformed_xml")

    def test_report_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self._write_archive(root,"demo","demo",{"z.pos.xml":POS_XML,"a.meta.xml":META_XML,"m.text.xml":TEXT_XML}); a=self.audit.audit_upstream(root); b=self.audit.audit_upstream(root)
        self.assertEqual(a,b); self.assertEqual(self.audit.render_report_json(a),self.audit.render_report_json(b))

if __name__=="__main__": unittest.main()
