import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "semantic_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_semantic_audit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load semantic audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TT_ONE = '''<meta corpus="demo" document_cts_urn="urn:cts:demo:one" segmentation="gold" tagging="checked" parsing="automatic" entities="gold" identities="none" redundant="no" license="CC-BY 4.0" title="One">
<translation translation="Hello">
<arabic arabic="مرحبا">
<pb_xml_id pb_xml_id="p1">
<cb_n cb_n="1">
<lb_n lb_n="1">
<orig_group orig_group="ⲁ">
<norm_group norm_group="ⲁ">
<orig orig="ⲁ">
<entity entity="person" identity="Demo" head_tok="#u1">
<norm xml:id="u1" func="root" pos="N" lemma="ⲁ" norm="ⲁ">
ⲁ
</norm>
</entity>
'''

TT_TWO = '''<meta corpus="packed" document_cts_urn="urn:cts:demo:two" segmentation="checked" tagging="checked" parsing="gold" entities="checked" identities="checked" redundant="yes" witness="urn:cts:demo:one" license="CUSTOM" title="Two">
<orig_group orig_group="ⲃ"><norm_group norm_group="ⲃ"><orig orig="ⲃ"><norm xml:id="u1" func="root" norm="ⲃ">ⲃ</norm>
'''


class SemanticAuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_parse_meta_line_decodes_xml_entities_without_parsing_overlap_sgml(self):
        attrs = self.audit.parse_meta_line(
            '<meta title="A &amp; B" license="&lt;a href=\'x\'&gt;CC&lt;/a&gt;">'
        )
        self.assertEqual(attrs["title"], "A & B")
        self.assertEqual(attrs["license"], "<a href='x'>CC</a>")

    def test_source_native_meta_lexer_preserves_and_classifies_duplicates(self):
        parsed = self.audit.scan_meta_line(
            '<meta title="A &amp; B" people="A" people="A" places="X" places="Y">'
        )
        self.assertEqual(parsed["attributes"]["title"], "A & B")
        self.assertEqual(parsed["attributes"]["people"], "A")
        self.assertEqual(parsed["attributes"]["places"], "X")
        self.assertEqual(
            parsed["duplicates"],
            {
                "people": {"values": ["A", "A"], "conflict": False},
                "places": {"values": ["X", "Y"], "conflict": True},
            },
        )

    def test_audits_directory_and_zip_packed_tt_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "demo" / "demo_TT"
            direct.mkdir(parents=True)
            (direct / "one.tt").write_text(TT_ONE, encoding="utf-8")

            packed_dir = root / "packed"
            packed_dir.mkdir()
            with zipfile.ZipFile(packed_dir / "packed_TT.zip", "w") as archive:
                archive.writestr("packed_TT/two.tt", TT_TWO)
                archive.writestr("packed_TT/README.txt", "ignore")

            (root / "meta.json").write_text(
                json.dumps({"demo:one": {"title": "One"}, "packed:two": {"title": "Two"}}),
                encoding="utf-8",
            )

            report = self.audit.audit_upstream(root)

        self.assertEqual(report["document_count"], 2)
        self.assertEqual(report["source_packaging"], {"archive": 1, "directory": 1})
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["quality_values"]["segmentation"], {"checked": 1, "gold": 1})
        self.assertEqual(report["redundant_values"], {"no": 1, "yes": 1})
        self.assertEqual(report["license_values"], {"CC-BY 4.0": 1, "CUSTOM": 1})
        self.assertEqual(report["missing_metadata"]["document_cts_urn"], 0)
        self.assertEqual(report["missing_metadata_records"], [])
        self.assertEqual(report["layer_presence"]["orig_group"], 2)
        self.assertEqual(report["layer_presence"]["dependency_func"], 2)
        self.assertEqual(report["layer_presence"]["dependency_head"], 0)
        self.assertEqual(report["layer_presence"]["entity"], 1)
        self.assertEqual(report["layer_presence"]["entity_identity"], 1)
        self.assertEqual(report["layer_presence"]["entity_head_tok"], 1)
        self.assertEqual(report["layer_presence"]["translation"], 1)
        self.assertEqual(report["layer_presence"]["arabic_translation"], 1)
        self.assertEqual(report["layer_presence"]["page"], 1)
        self.assertEqual(report["layer_presence"]["column"], 1)
        self.assertEqual(report["layer_presence"]["line"], 1)
        self.assertEqual(report["duplicate_meta_attributes"]["document_count"], 0)
        self.assertEqual(report["meta_json"]["present"], True)
        self.assertEqual(report["meta_json"]["top_level_type"], "object")
        self.assertEqual(report["meta_json"]["top_level_size"], 2)
        self.assertEqual(report["meta_json"]["sample_keys"], ["demo:one", "packed:two"])

    def test_missing_metadata_records_preserve_source_identity(self):
        missing_license = '''<meta corpus="demo" document_cts_urn="urn:cts:demo:missing" segmentation="gold" tagging="gold" parsing="gold" entities="gold" identities="gold" redundant="no" title="Missing">
<norm xml:id="u1" func="root" norm="x">x</norm>
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "demo" / "demo_TT"
            direct.mkdir(parents=True)
            (direct / "missing.tt").write_text(missing_license, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["missing_metadata"]["license"], 1)
        self.assertEqual(
            report["missing_metadata_records"],
            [
                {
                    "field": "license",
                    "source": "demo/demo_TT/missing.tt",
                    "corpus": "demo",
                    "document_cts_urn": "urn:cts:demo:missing",
                }
            ],
        )

    def test_duplicate_metadata_is_measured_without_silent_overwrite(self):
        duplicate = '''<meta corpus="demo" document_cts_urn="urn:cts:demo:dup" license="CC" title="Dup" people="A" people="A" places="X" places="Y">
<norm xml:id="u1" func="root" norm="x">x</norm>
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "demo" / "demo_TT"
            direct.mkdir(parents=True)
            (direct / "dup.tt").write_text(duplicate, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["errors"], [])
        summary = report["duplicate_meta_attributes"]
        self.assertEqual(summary["document_count"], 1)
        self.assertEqual(summary["equal_value_occurrences"], 1)
        self.assertEqual(summary["conflicting_occurrences"], 1)
        self.assertEqual(summary["key_document_counts"], {"people": 1, "places": 1})
        self.assertEqual(
            summary["conflict_examples"],
            [
                {
                    "source": "demo/demo_TT/dup.tt",
                    "key": "places",
                    "values": ["X", "Y"],
                }
            ],
        )

    def test_missing_or_malformed_meta_is_reported_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "broken" / "broken_TT"
            direct.mkdir(parents=True)
            (direct / "missing.tt").write_text("<orig_group orig_group=\"x\">x", encoding="utf-8")
            (direct / "malformed.tt").write_text("<meta title=\"unterminated>\n", encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["document_count"], 2)
        self.assertEqual(len(report["errors"]), 2)
        kinds = sorted(error["kind"] for error in report["errors"])
        self.assertEqual(kinds, ["malformed_meta", "missing_meta"])

    def test_report_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "demo" / "demo_TT"
            direct.mkdir(parents=True)
            (direct / "b.tt").write_text(TT_TWO, encoding="utf-8")
            (direct / "a.tt").write_text(TT_ONE, encoding="utf-8")
            first = self.audit.audit_upstream(root)
            second = self.audit.audit_upstream(root)
        self.assertEqual(first, second)
        self.assertEqual(
            self.audit.render_report_json(first),
            self.audit.render_report_json(second),
        )


if __name__ == "__main__":
    unittest.main()
