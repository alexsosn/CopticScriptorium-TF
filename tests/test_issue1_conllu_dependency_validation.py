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
        report = self._audit("bad", source)
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
        report = self._audit("ok", source)
        self.assertEqual(report["errors"], [])

    def test_duplicate_basic_token_id_is_rejected(self):
        source = '''# sent_id = duplicate-s1
1\ta\ta\tNOUN\tN\t_\t0\troot\t_\t_
1\tb\tb\tNOUN\tN\t_\t0\troot\t_\t_
'''
        report = self._audit("duplicate", source)
        self.assertEqual(
            report["errors"],
            [
                {
                    "kind": "duplicate_token_id",
                    "source": "duplicate/duplicate_CONLLU/duplicate.conllu",
                    "line": 3,
                    "id": "1",
                }
            ],
        )

    def test_malformed_multiword_and_empty_node_ids_are_not_accepted_by_punctuation(self):
        source = '''# sent_id = malformed-s1
foo-bar\tx\t_\t_\t_\t_\t_\t_\t_\t_
a.b\tx\t_\t_\t_\t_\t_\t_\t_\t_
1\ta\ta\tNOUN\tN\t_\t0\troot\t_\t_
'''
        report = self._audit("malformed", source)
        self.assertEqual(
            report["errors"],
            [
                {
                    "kind": "invalid_id",
                    "source": "malformed/malformed_CONLLU/malformed.conllu",
                    "line": 2,
                    "id": "foo-bar",
                },
                {
                    "kind": "invalid_id",
                    "source": "malformed/malformed_CONLLU/malformed.conllu",
                    "line": 3,
                    "id": "a.b",
                },
            ],
        )
        self.assertEqual(report["multiword_rows"], 0)
        self.assertEqual(report["empty_node_rows"], 0)

    def _audit(self, name: str, source: str):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / name / f"{name}_CONLLU"
            directory.mkdir(parents=True)
            (directory / f"{name}.conllu").write_text(source, encoding="utf-8")
            return self.audit.audit_upstream(root)


if __name__ == "__main__":
    unittest.main()
