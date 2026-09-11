import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_shape_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_zero_span_translation", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph shape audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture() -> str:
    return (
        '<meta corpus="demo" document_cts_urn="urn:cts:demo:one" title="Demo">\n'
        '<norm_group norm_group="a"><orig orig="a">\n'
        '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a</norm>\n'
        '</orig></norm_group>\n'
        '<translation translation="independently positioned note"></translation>\n'
        '<norm_group norm_group="b"><orig orig="b">\n'
        '<norm xml:id="u2" new_sent="true" func="root" pos="N" lemma="b" norm="b">b</norm>\n'
        '</orig></norm_group>\n'
    )


class ZeroSpanTranslationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_zero_token_translation_preserves_literal_text_and_source_order_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "demo" / "demo_TT"
            directory.mkdir(parents=True)
            text = fixture()
            (directory / "one.tt").write_text(text, encoding="utf-8")

            report = self.audit.audit_upstream(root)
            self.assertEqual(report["zero_token_translation_count"], 1)
            self.assertEqual(
                report["zero_token_translations"],
                [
                    {
                        "source_record_id": "demo/demo:one",
                        "source": "demo/demo_TT/one.tt",
                        "text": "independently positioned note",
                        "after_token_position": 1,
                        "source_char_offset": text.index(
                            '<translation translation="independently positioned note">'
                        ),
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
