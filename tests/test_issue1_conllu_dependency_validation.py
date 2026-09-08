import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "conllu_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_conllu_validation", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load CoNLL-U audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConlluDependencyValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_reports_nonpositive_token_ids_negative_heads_and_dangling_heads(self):
        source = '''# sent_id = bad-s1
0\tx\tx\tX\tX\t_\t2\tdep\t_\t_
1\ta\ta\tNOUN\tN\t_\t3\tdep\t_\t_
2\tb\tb\tVERB\tV\t_\t-1\troot\t_\t_
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "bad" / "bad_CONLLU"
            directory.mkdir(parents=True)
            (directory / "bad.conllu").write_text(source, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(
            report["errors"],
            [
                {
                    "kind": "invalid_token_id",
                    "source": "bad/bad_CONLLU/bad.conllu",
                    "line": 2,
                    "id": "0",
                },
                {
                    "kind": "dangling_head",
                    "source": "bad/bad_CONLLU/bad.conllu",
                    "line": 3,
                    "head": "3",
                },
                {
                    "kind": "invalid_head",
                    "source": "bad/bad_CONLLU/bad.conllu",
                    "line": 4,
                    "head": "-1",
                },
            ],
        )

    def test_valid_forward_head_reference_is_accepted_after_sentence_is_known(self):
        source = '''# sent_id = ok-s1
1\ta\ta\tNOUN\tN\t_\t2\tnsubj\t_\t_
2\tb\tb\tVERB\tV\t_\t0\troot\t_\t_
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "ok" / "ok_CONLLU"
            directory.mkdir(parents=True)
            (directory / "ok.conllu").write_text(source, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["errors"], [])


if __name__ == "__main__":
    unittest.main()
