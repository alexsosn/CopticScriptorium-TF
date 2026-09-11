import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_shape_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_entity_head_span", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph shape audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tt(root: Path, body: str) -> None:
    directory = root / "demo" / "demo_TT"
    directory.mkdir(parents=True)
    text = '<meta corpus="demo" document_cts_urn="urn:cts:demo:one" title="Demo">\n' + body
    (directory / "one.tt").write_text(text, encoding="utf-8")


class EntityHeadSpanContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_entity_opened_inside_current_norm_inherits_that_word_locus(self):
        body = (
            '<norm_group norm_group="ab">\n'
            '<orig orig="a">\n'
            '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">\n'
            'a\n'
            '<entity entity="abstract" head_tok="#u1" text="a b">\n'
            'a\n'
            '</norm>\n'
            '</orig>\n'
            '<orig orig="b">\n'
            '<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="b" norm="b">b</norm>\n'
            '</orig>\n'
            '</entity>\n'
            '</norm_group>\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(root, body)
            report = self.audit.audit_upstream(root)
            self.assertEqual(report["entity_count"], 1)
            self.assertEqual(report["entity_unresolved_head_count"], 0)
            self.assertEqual(report["entity_head_outside_span_count"], 0)
            self.assertEqual(report["entity_heads_outside_span"], [])
            self.assertEqual(report["entity_token_count_histogram"], {"2": 1})

    def test_genuinely_external_resolved_head_is_still_measured(self):
        body = (
            '<norm_group norm_group="ab">\n'
            '<orig orig="a">\n'
            '<entity entity="person" identity="Person A" head_tok="#u2" text="a">\n'
            '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a</norm>\n'
            '</entity>\n'
            '</orig>\n'
            '<orig orig="b">\n'
            '<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="b" norm="b">b</norm>\n'
            '</orig>\n'
            '</norm_group>\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(root, body)
            report = self.audit.audit_upstream(root)
            self.assertEqual(report["entity_count"], 1)
            self.assertEqual(report["entity_unresolved_head_count"], 0)
            self.assertEqual(report["entity_head_outside_span_count"], 1)
            self.assertEqual(
                report["entity_heads_outside_span"],
                [
                    {
                        "source_record_id": "demo/demo:one",
                        "source": "demo/demo_TT/one.tt",
                        "entity_class": "person",
                        "identity": "Person A",
                        "head_tok": "#u2",
                        "target_token_id": "u2",
                        "span_token_ids": ["u1"],
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
