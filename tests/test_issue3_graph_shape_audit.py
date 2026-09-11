import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_shape_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_graph_shape_audit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph shape audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def crossing_tt() -> str:
    return (
        '<meta corpus="demo" document_cts_urn="urn:cts:demo:one" title="Demo">\n'
        '<translation translation="hello">\n'
        '<lb_n lb_n="1">\n'
        '<orig_group orig_group="abc">\n'
        '<norm_group norm_group="abc">\n'
        '<entity entity="person" identity="Demo Person" head_tok="#u1" text="abc">\n'
        '<orig orig="abc">\n'
        '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="abc" norm="abc">\n'
        'ab\n'
        '</lb_n>\n'
        '<lb_n lb_n="2">\n'
        'c\n'
        '</norm>\n'
        '</orig>\n'
        '</entity>\n'
        '</norm_group>\n'
        '</orig_group>\n'
        '</lb_n>\n'
        '</translation>\n'
    )


def write_direct(root: Path, text: str) -> None:
    directory = root / "demo" / "demo_TT"
    directory.mkdir(parents=True)
    (directory / "one.tt").write_text(text, encoding="utf-8")


def write_archive(root: Path, data: bytes) -> None:
    corpus = root / "demo"
    corpus.mkdir(parents=True)
    with zipfile.ZipFile(corpus / "demo_TT.zip", "w") as archive:
        archive.writestr("demo_TT/one.tt", data)


class GraphShapeAuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_measures_linguistic_hierarchy_entity_sentence_and_translation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_direct(root, crossing_tt())
            report = self.audit.audit_upstream(root)

            self.assertEqual(report["document_count"], 1)
            self.assertEqual(report["norm_token_count"], 1)
            self.assertEqual(report["orig_segment_count"], 1)
            self.assertEqual(report["norm_group_count"], 1)
            self.assertEqual(report["orig_group_count"], 1)
            self.assertEqual(report["sentence_start_count"], 1)
            self.assertEqual(report["documents_without_sentence_start"], [])
            self.assertEqual(report["entity_count"], 1)
            self.assertEqual(report["entity_missing_head_count"], 0)
            self.assertEqual(report["entity_unresolved_head_count"], 0)
            self.assertEqual(report["translation_count"], 1)
            self.assertEqual(report["arabic_translation_count"], 0)
            self.assertEqual(report["group_cardinalities"]["orig_group_to_norm_group"], {"1": 1})
            self.assertEqual(report["group_cardinalities"]["norm_group_to_orig"], {"1": 1})
            self.assertEqual(report["group_cardinalities"]["orig_to_norm"], {"1": 1})

    def test_records_line_transition_inside_one_norm_token_without_splitting_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_direct(root, crossing_tt())
            report = self.audit.audit_upstream(root)

            self.assertEqual(report["layout_node_counts"]["line"], 2)
            self.assertEqual(report["token_internal_layout_crossing_count"], 1)
            crossing = report["token_internal_layout_crossings"][0]
            self.assertEqual(crossing["source_record_id"], "demo/demo:one")
            self.assertEqual(crossing["token_id"], "u1")
            self.assertEqual(crossing["kind"], "line")
            self.assertEqual(crossing["from_value"], "1")
            self.assertEqual(crossing["to_value"], "2")
            self.assertEqual(crossing["char_offset"], 2)
            self.assertEqual(crossing["token_text"], "abc")

    def test_direct_and_archive_packaging_produce_same_semantic_census(self):
        with tempfile.TemporaryDirectory() as direct_tmp, tempfile.TemporaryDirectory() as archive_tmp:
            direct = Path(direct_tmp)
            archive = Path(archive_tmp)
            text = crossing_tt()
            write_direct(direct, text)
            write_archive(archive, text.encode("utf-8"))
            direct_report = self.audit.audit_upstream(direct)
            archive_report = self.audit.audit_upstream(archive)

            for key in (
                "document_count",
                "norm_token_count",
                "orig_segment_count",
                "norm_group_count",
                "orig_group_count",
                "sentence_start_count",
                "entity_count",
                "translation_count",
                "layout_node_counts",
                "group_cardinalities",
                "token_internal_layout_crossing_count",
            ):
                self.assertEqual(direct_report[key], archive_report[key])

    def test_invalid_utf8_fails_closed_for_direct_and_archive_tt(self):
        invalid = b'<meta corpus="demo">\n\xff\n'
        for packaging in ("directory", "archive"):
            with self.subTest(packaging=packaging), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                if packaging == "directory":
                    directory = root / "demo" / "demo_TT"
                    directory.mkdir(parents=True)
                    (directory / "bad.tt").write_bytes(invalid)
                else:
                    write_archive(root, invalid)
                with self.assertRaises(UnicodeDecodeError):
                    self.audit.audit_upstream(root)

    def test_report_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_direct(root, crossing_tt())
            first = self.audit.audit_upstream(root)
            second = self.audit.audit_upstream(root)
            self.assertEqual(first, second)
            self.assertEqual(
                self.audit.render_report_json(first),
                self.audit.render_report_json(second),
            )


if __name__ == "__main__":
    unittest.main()
