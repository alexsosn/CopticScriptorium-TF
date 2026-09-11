import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_shape_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_graph_shape_extended", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph shape audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tt(root: Path, text: str) -> None:
    directory = root / "demo" / "demo_TT"
    directory.mkdir(parents=True)
    (directory / "one.tt").write_text(text, encoding="utf-8")


def multi_crossing_tt() -> str:
    return (
        '<meta corpus="demo" document_cts_urn="urn:cts:demo:one" title="Demo">\n'
        '<pb_xml_id pb_xml_id="p1">\n'
        '<cb_n cb_n="1">\n'
        '<lb_n lb_n="1">\n'
        '<norm_group norm_group="abcdef">\n'
        '<orig orig="abcdef">\n'
        '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="abcdef" norm="abcdef">\n'
        'ab\n'
        '</lb_n>\n'
        '<lb_n lb_n="2">\n'
        'cd\n'
        '</cb_n>\n'
        '<cb_n cb_n="2">\n'
        '</pb_xml_id>\n'
        '<pb_xml_id pb_xml_id="p2">\n'
        'ef\n'
        '</norm>\n'
        '</orig>\n'
        '</norm_group>\n'
        '</lb_n>\n'
        '</cb_n>\n'
        '</pb_xml_id>\n'
    )


def entity_translation_tt() -> str:
    return (
        '<meta corpus="demo" document_cts_urn="urn:cts:demo:one" title="Demo">\n'
        '<chapter_n chapter_n="1">\n'
        '<verse_n verse_n="1">\n'
        '<vid_n vid_n="v1">\n'
        '<translation translation="hello">\n'
        '<entity entity="person" identity="Person A" head_tok="#u1" text="ab">\n'
        '<entity entity="place" head_tok="#u1" text="a">\n'
        '<norm_group norm_group="a">\n'
        '<orig orig="a">\n'
        '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a</norm>\n'
        '</orig>\n'
        '</norm_group>\n'
        '</entity>\n'
        '<norm_group norm_group="b">\n'
        '<orig orig="b">\n'
        '<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="b" norm="b">b</norm>\n'
        '</orig>\n'
        '</norm_group>\n'
        '</entity>\n'
        '</translation>\n'
        '<translation translation="">\n'
        '<norm_group norm_group="c">\n'
        '<orig orig="c">\n'
        '<norm xml:id="u3" new_sent="true" func="root" pos="N" lemma="c" norm="c">c</norm>\n'
        '</orig>\n'
        '</norm_group>\n'
        '</translation>\n'
        '<translation translation=""></translation>\n'
        '</vid_n>\n'
        '</verse_n>\n'
        '</chapter_n>\n'
    )


class ExtendedGraphShapeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_aggregates_multiple_layout_boundaries_inside_one_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(root, multi_crossing_tt())
            report = self.audit.audit_upstream(root)

            self.assertEqual(report["token_internal_layout_crossing_count"], 3)
            self.assertEqual(report["tokens_with_internal_layout_crossing_count"], 1)
            self.assertEqual(report["tokens_with_multiple_internal_layout_crossings_count"], 1)
            self.assertEqual(report["max_internal_layout_crossings_per_token"], 3)
            self.assertEqual(
                report["token_internal_layout_crossing_kind_counts"],
                {"column": 1, "line": 1, "page": 1},
            )

    def test_measures_entity_classes_identities_and_nested_entities(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(root, entity_translation_tt())
            report = self.audit.audit_upstream(root)

            self.assertEqual(report["entity_count"], 2)
            self.assertEqual(report["nested_entity_count"], 1)
            self.assertEqual(report["entity_class_counts"], {"person": 1, "place": 1})
            self.assertEqual(report["entity_identity_count"], 1)
            self.assertEqual(report["entity_without_identity_count"], 1)

    def test_translation_locus_distinguishes_empty_text_from_zero_token_span(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(root, entity_translation_tt())
            report = self.audit.audit_upstream(root)

            self.assertEqual(report["translation_count"], 3)
            self.assertEqual(report["empty_translation_count"], 2)
            self.assertEqual(report["translation_token_count_histogram"], {"0": 1, "1": 1, "2": 1})
            self.assertEqual(report["zero_token_translation_count"], 1)
            self.assertEqual(report["empty_zero_token_translation_count"], 1)

    def test_reports_document_coverage_for_nonuniversal_source_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(root, entity_translation_tt())
            report = self.audit.audit_upstream(root)

            self.assertEqual(report["documents_with_chapter_markers"], 1)
            self.assertEqual(report["documents_with_verse_markers"], 1)
            self.assertEqual(report["documents_with_video_markers"], 1)
            self.assertEqual(report["documents_with_translation"], 1)
            self.assertEqual(report["documents_with_arabic_translation"], 0)


if __name__ == "__main__":
    unittest.main()
