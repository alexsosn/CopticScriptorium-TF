import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "cross_format_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_cross_format_invalid", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load cross-format audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TT = '''<meta corpus="demo" document_cts_urn="urn:cts:demo:one">
<norm xml:id="u1" func="root" pos="V" lemma="a" norm="a">a</norm>
<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="b" norm="b">b</norm>
'''


class CrossFormatInvalidConlluTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_nonpositive_token_id_is_malformed_source_not_semantic_parity(self):
        conllu = '''# sent_id = bad-1
0\ta\ta\tVERB\tV\t_\t2\tdep\t_\t_
1\tb\tb\tNOUN\tN\t_\t0\troot\t_\t_
'''
        report = self._audit(conllu)
        self.assertEqual(report["compared_document_count"], 0)
        self.assertEqual(report["token_count_mismatches"], [])
        self.assertEqual(
            report["malformed_conllu_documents"],
            [
                {
                    "dataset": "demo/demo",
                    "record": "one",
                    "source": "demo/demo_CONLLU/one.conllu",
                    "error": "invalid CoNLL-U token id 0 at line 2",
                }
            ],
        )

    def test_negative_head_is_malformed_source_not_semantic_parity(self):
        conllu = '''# sent_id = bad-1
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
2\tb\tb\tNOUN\tN\t_\t-1\tobj\t_\t_
'''
        report = self._audit(conllu)
        self.assertEqual(report["compared_document_count"], 0)
        self.assertEqual(report["token_count_mismatches"], [])
        self.assertEqual(len(report["malformed_conllu_documents"]), 1)
        self.assertEqual(
            report["malformed_conllu_documents"][0]["error"],
            "invalid CoNLL-U HEAD -1 at line 3",
        )

    def test_malformed_multiword_or_empty_node_id_is_not_silently_ignored(self):
        conllu = '''# sent_id = bad-1
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
foo-bar\tab\t_\t_\t_\t_\t_\t_\t_\t_
2\tb\tb\tNOUN\tN\t_\t1\tobj\t_\t_
'''
        report = self._audit(conllu)
        self.assertEqual(report["compared_document_count"], 0)
        self.assertEqual(report["token_count_mismatches"], [])
        self.assertEqual(len(report["malformed_conllu_documents"]), 1)
        self.assertEqual(
            report["malformed_conllu_documents"][0]["error"],
            "invalid CoNLL-U row id 'foo-bar' at line 3",
        )

    def test_valid_multiword_and_empty_node_rows_are_ignored_for_basic_parity(self):
        conllu = '''# sent_id = ok-1
1-2\tab\t_\t_\t_\t_\t_\t_\t_\t_
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
2\tb\tb\tNOUN\tN\t_\t1\tobj\t_\t_
2.1\tx\tx\tX\tX\t_\t_\tdep\t_\t_
'''
        report = self._audit(conllu)
        self.assertEqual(report["malformed_conllu_documents"], [])
        self.assertEqual(report["compared_document_count"], 1)
        self.assertEqual(report["field_mismatch_counts"]["norm"], 0)

    def _audit(self, conllu: str):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "demo" / "demo_TT"
            conllu_dir = root / "demo" / "demo_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)
            (tt_dir / "one.tt").write_text(TT, encoding="utf-8")
            (conllu_dir / "one.conllu").write_text(conllu, encoding="utf-8")
            return self.audit.audit_upstream(root)


if __name__ == "__main__":
    unittest.main()
