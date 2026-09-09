import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONLLU_PATH = ROOT / "research" / "issue-1" / "conllu_audit.py"
CROSS_PATH = ROOT / "research" / "issue-1" / "cross_format_audit.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TT_TWO = '''<meta corpus="demo" document_cts_urn="urn:cts:demo:one">
<norm xml:id="u1" func="root" pos="V" lemma="a" norm="a">a</norm>
<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="b" norm="b">b</norm>
'''

TT_THREE = '''<meta corpus="demo" document_cts_urn="urn:cts:demo:one">
<norm xml:id="u1" func="root" pos="V" lemma="a" norm="a">a</norm>
<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="b" norm="b">b</norm>
<norm xml:id="u3" func="obj" head="#u1" pos="N" lemma="c" norm="c">c</norm>
'''


class ConlluSharedIdContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conllu = load_module("issue1_conllu_contract", CONLLU_PATH)
        cls.cross = load_module("issue1_cross_contract", CROSS_PATH)

    def _audit_both(self, conllu_text: str, tt_text: str = TT_TWO):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "demo" / "demo_TT"
            conllu_dir = root / "demo" / "demo_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)
            (tt_dir / "one.tt").write_text(tt_text, encoding="utf-8")
            (conllu_dir / "one.conllu").write_text(conllu_text, encoding="utf-8")
            return self.conllu.audit_upstream(root), self.cross.audit_upstream(root)

    def _assert_invalid_in_both(self, conllu_text: str, tt_text: str = TT_TWO):
        standalone, cross = self._audit_both(conllu_text, tt_text)
        self.assertTrue(standalone["errors"], "standalone audit accepted invalid ID structure")
        self.assertEqual(cross["compared_document_count"], 0)
        self.assertEqual(len(cross["malformed_conllu_documents"]), 1)

    def test_sentence_initial_empty_node_zero_dot_one_is_valid(self):
        source = '''# sent_id = empty-initial
0.1\tghost\tghost\tX\tX\t_\t_\t_\t0:dep\t_
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
2\tb\tb\tNOUN\tN\t_\t1\tobj\t_\t_
'''
        standalone, cross = self._audit_both(source)
        self.assertEqual(standalone["errors"], [])
        self.assertEqual(standalone["empty_node_rows"], 1)
        self.assertEqual(cross["malformed_conllu_documents"], [])
        self.assertEqual(cross["compared_document_count"], 1)

    def test_basic_word_ids_must_be_consecutive_from_one(self):
        source = '''# sent_id = gap
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
3\tb\tb\tNOUN\tN\t_\t1\tobj\t_\t_
'''
        self._assert_invalid_in_both(source)

    def test_reversed_multiword_range_is_invalid_in_both(self):
        source = '''# sent_id = reversed
2-1\tab\t_\t_\t_\t_\t_\t_\t_\t_
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
2\tb\tb\tNOUN\tN\t_\t1\tobj\t_\t_
'''
        self._assert_invalid_in_both(source)

    def test_overlapping_multiword_ranges_are_invalid(self):
        source = '''# sent_id = overlap
1-2\tab\t_\t_\t_\t_\t_\t_\t_\t_
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
2-3\tbc\t_\t_\t_\t_\t_\t_\t_\t_
2\tb\tb\tNOUN\tN\t_\t1\tobj\t_\t_
3\tc\tc\tNOUN\tN\t_\t1\tobj\t_\t_
'''
        self._assert_invalid_in_both(source, TT_THREE)

    def test_multiword_range_must_precede_first_word(self):
        source = '''# sent_id = misplaced
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
1-2\tab\t_\t_\t_\t_\t_\t_\t_\t_
2\tb\tb\tNOUN\tN\t_\t1\tobj\t_\t_
'''
        self._assert_invalid_in_both(source)

    def test_empty_node_fractional_indices_cannot_skip_dot_one(self):
        source = '''# sent_id = empty-gap
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
1.2\tghost\tghost\tX\tX\t_\t_\t_\t1:dep\t_
2\tb\tb\tNOUN\tN\t_\t1\tobj\t_\t_
'''
        self._assert_invalid_in_both(source)


if __name__ == "__main__":
    unittest.main()
