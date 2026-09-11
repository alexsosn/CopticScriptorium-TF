import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_shape_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_arabic_translation", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph shape audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture() -> str:
    return (
        '<meta corpus="demo" document_cts_urn="urn:cts:demo:one" title="Demo">\n'
        '<norm_group norm_group="a"><orig orig="a">\n'
        '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">\n'
        '<arabic arabic="داخل الكلمة">a</arabic>\n'
        'a\n'
        '</norm>\n'
        '</orig></norm_group>\n'
        '<arabic arabic="ترجمة">\n'
        '<norm_group norm_group="b"><orig orig="b">\n'
        '<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="b" norm="b">b</norm>\n'
        '</orig></norm_group>\n'
        '</arabic>\n'
        '<arabic arabic="ملاحظة مستقلة"></arabic>\n'
    )


class ArabicTranslationLocusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_arabic_translation_inherits_current_word_locus_before_zero_span_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "demo" / "demo_TT"
            directory.mkdir(parents=True)
            text = fixture()
            (directory / "one.tt").write_text(text, encoding="utf-8")

            report = self.audit.audit_upstream(root)
            self.assertEqual(report["arabic_translation_count"], 3)
            self.assertEqual(
                report["arabic_translation_token_count_histogram"],
                {"0": 1, "1": 2},
            )
            self.assertEqual(report["zero_token_arabic_translation_count"], 1)
            self.assertEqual(
                report["zero_token_arabic_translations"],
                [
                    {
                        "source_record_id": "demo/demo:one",
                        "source": "demo/demo_TT/one.tt",
                        "text": "ملاحظة مستقلة",
                        "after_token_position": 2,
                        "source_char_offset": text.index(
                            '<arabic arabic="ملاحظة مستقلة">'
                        ),
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
