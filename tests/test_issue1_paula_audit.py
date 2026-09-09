import importlib.util
import json
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
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TEXT_XML = '''<?xml version="1.0"?>
<paula version="1.1"><header paula_id="doc.text"/><body>abc</body></paula>
'''
TOK_XML = '''<?xml version="1.0"?>
<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink">
<header paula_id="doc.tok"/>
<markList type="tok" xml:base="doc.text.xml"><mark id="tok_1" xlink:href="#xpointer(string-range(//body,'',1,1))"/></markList>
</paula>
'''
POS_XML = '''<?xml version="1.0"?>
<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink">
<header paula_id="doc.pos"/>
<featList type="pos" xml:base="doc.tok.xml"><feat xlink:href="#tok_1" value="N"/></featList>
</paula>
'''
META_XML = '''<?xml version="1.0"?>
<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink">
<header paula_id="demo.meta_license"/>
<featList type="license" xml:base="demo.anno.xml"><feat xlink:href="#anno_1" value="CC-BY 4.0"/></featList>
</paula>
'''
ANNOFEAT_XML = '''<?xml version="1.0"?>
<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink">
<header paula_id="demo.annoFeat"/>
<featList type="annoFeat" xml:base="demo.anno.xml"><feat xlink:href="#rel_1" value="tok"/></featList>
</paula>
'''
MULTI_META_XML = '''<?xml version="1.0"?>
<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink">
<header paula_id="demo.meta_multiFeat"/>
<multiFeatList type="multiFeat" xml:base="demo.anno.xml">
  <multiFeat xlink:href="#anno_1">
    <feat name="language" value="Coptic"/>
    <feat name="source_format" value="PAULA XML"/>
  </multiFeat>
</multiFeatList>
</paula>
'''
REL_XML = '''<?xml version="1.0"?>
<paula version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink">
<header paula_id="doc.dep"/>
<relList type="dep" xml:base="doc.tok.xml"><rel id="rel_1" xlink:href="#tok_1" target="#tok_1"/></relList>
</paula>
'''


class PaulaAuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def _write_archive(self, root: Path, corpus: str, dataset: str, members: dict[str, str], nested: bool = False):
        corpus_dir = root / corpus
        corpus_dir.mkdir(parents=True, exist_ok=True)
        if nested:
            package_dir = corpus_dir / f"{dataset}_PAULA"
            package_dir.mkdir()
            archive_path = package_dir / f"{dataset}_PAULA.zip"
        else:
            archive_path = corpus_dir / f"{dataset}_PAULA.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        return archive_path

    def test_inventories_paula_xml_kinds_and_metadata_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_archive(
                root,
                "demo",
                "demo",
                {
                    "demo/doc/doc.text.xml": TEXT_XML,
                    "demo/doc/doc.tok.xml": TOK_XML,
                    "demo/doc/doc.pos.xml": POS_XML,
                    "demo/demo.meta_license.xml": META_XML,
                    "demo/doc/doc.dep.xml": REL_XML,
                    "demo/paula_feat.dtd": "ignored",
                },
            )

            report = self.audit.audit_upstream(root)

        self.assertEqual(report["source_package_count"], 1)
        self.assertEqual(report["parsed_package_count"], 1)
        self.assertEqual(report["packaging"], {"archive": 1})
        self.assertEqual(report["xml_member_count"], 5)
        self.assertEqual(
            report["element_kind_counts"],
            {"body": 1, "featList": 2, "markList": 1, "relList": 1},
        )
        self.assertEqual(
            report["list_type_occurrences"],
            {
                "featList": {"license": 1, "pos": 1},
                "markList": {"tok": 1},
                "relList": {"dep": 1},
            },
        )
        self.assertEqual(report["metadata_feature_type_occurrences"], {"license": 1})
        self.assertEqual(
            report["metadata_feature_instances"],
            [
                {
                    "dataset": "demo/demo",
                    "source": "demo/demo_PAULA.zip!/demo/demo.meta_license.xml",
                    "paula_id": "demo.meta_license",
                    "base": "demo.anno.xml",
                    "type": "license",
                    "values": ["CC-BY 4.0"],
                }
            ],
        )
        self.assertEqual(report["errors"], [])

    def test_annofeat_is_not_metadata_and_multifeat_metadata_is_expanded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_archive(
                root,
                "demo",
                "demo",
                {
                    "demo/demo.anno_feat.xml": ANNOFEAT_XML,
                    "demo/demo.meta_multiFeat.xml": MULTI_META_XML,
                },
            )

            report = self.audit.audit_upstream(root)

        self.assertEqual(
            report["list_type_occurrences"],
            {
                "featList": {"annoFeat": 1},
                "multiFeatList": {"multiFeat": 1},
            },
        )
        self.assertEqual(
            report["metadata_feature_type_occurrences"],
            {"language": 1, "source_format": 1},
        )
        self.assertEqual(
            report["metadata_feature_instances"],
            [
                {
                    "dataset": "demo/demo",
                    "source": "demo/demo_PAULA.zip!/demo/demo.meta_multiFeat.xml",
                    "paula_id": "demo.meta_multiFeat",
                    "base": "demo.anno.xml",
                    "type": "language",
                    "values": ["Coptic"],
                },
                {
                    "dataset": "demo/demo",
                    "source": "demo/demo_PAULA.zip!/demo/demo.meta_multiFeat.xml",
                    "paula_id": "demo.meta_multiFeat",
                    "base": "demo.anno.xml",
                    "type": "source_format",
                    "values": ["PAULA XML"],
                },
            ],
        )

    def test_nested_archive_packaging_is_counted_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_archive(
                root,
                "nested",
                "nested",
                {"nested/doc.text.xml": TEXT_XML},
                nested=True,
            )

            report = self.audit.audit_upstream(root)

        self.assertEqual(report["source_package_count"], 1)
        self.assertEqual(report["parsed_package_count"], 1)
        self.assertEqual(report["datasets"], ["nested/nested"])

    def test_malformed_xml_is_reported_with_member_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_archive(
                root,
                "broken",
                "broken",
                {
                    "broken/good.text.xml": TEXT_XML,
                    "broken/bad.xml": "<paula><broken>",
                },
            )

            report = self.audit.audit_upstream(root)

        self.assertEqual(report["source_package_count"], 1)
        self.assertEqual(report["parsed_package_count"], 1)
        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(report["errors"][0]["kind"], "malformed_xml")
        self.assertEqual(
            report["errors"][0]["source"],
            "broken/broken_PAULA.zip!/broken/bad.xml",
        )

    def test_report_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_archive(
                root,
                "demo",
                "demo",
                {
                    "z/doc.pos.xml": POS_XML,
                    "a/demo.meta_license.xml": META_XML,
                    "m/doc.text.xml": TEXT_XML,
                },
            )
            first = self.audit.audit_upstream(root)
            second = self.audit.audit_upstream(root)

        self.assertEqual(first, second)
        self.assertEqual(self.audit.render_report_json(first), self.audit.render_report_json(second))


if __name__ == "__main__":
    unittest.main()
