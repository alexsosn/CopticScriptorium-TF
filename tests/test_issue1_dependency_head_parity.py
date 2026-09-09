import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "cross_format_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_cross_format_head", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load cross-format audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TT = '''<meta corpus="demo" document_cts_urn="urn:cts:demo:one">
<norm xml:id="u1" func="root" pos="V" lemma="a" norm="a">a</norm>
<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="b" norm="b">b</norm>
<norm xml:id="u3" func="root" pos="V" lemma="c" norm="c">c</norm>
<norm xml:id="u4" func="obj" head="#u3" pos="N" lemma="d" norm="d">d</norm>
'''

CONLLU_MATCH = '''# sent_id = s1
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
2\tb\tb\tNOUN\tN\t_\t1\tobj\t_\t_

# sent_id = s2
1\tc\tc\tVERB\tV\t_\t0\troot\t_\t_
2\td\td\tNOUN\tN\t_\t1\tobj\t_\t_
'''

CONLLU_HEAD_DRIFT = CONLLU_MATCH.replace(
    "2\td\td\tNOUN\tN\t_\t1\tobj", "2\td\td\tNOUN\tN\t_\t0\tobj"
)


class DependencyHeadParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def _report(self, conllu: str):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "demo" / "demo_TT"
            conllu_dir = root / "demo" / "demo_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)
            (tt_dir / "one.tt").write_text(TT, encoding="utf-8")
            (conllu_dir / "one.conllu").write_text(conllu, encoding="utf-8")
            return self.audit.audit_upstream(root)

    def test_sentence_local_conllu_heads_are_normalized_to_document_positions(self):
        report = self._report(CONLLU_MATCH)
        self.assertEqual(report["field_mismatch_counts"]["head"], 0)

    def test_dependency_head_drift_is_reported_without_resolution(self):
        report = self._report(CONLLU_HEAD_DRIFT)
        self.assertEqual(report["field_mismatch_counts"]["head"], 1)
        examples = [e for e in report["field_mismatch_examples"] if e["field"] == "head"]
        self.assertEqual(
            examples,
            [
                {
                    "dataset": "demo/demo",
                    "record": "one",
                    "token_index": 4,
                    "field": "head",
                    "tt": 3,
                    "conllu": 0,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
