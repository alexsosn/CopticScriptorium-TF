import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "cross_format_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_cross_format_categories", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load cross-format audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CrossFormatMismatchCategoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_distinguishes_missing_values_from_true_conflicts(self):
        tt = '''<meta corpus="demo">
<norm xml:id="u1" func="root" pos="V" lemma="a" norm="a">a</norm>
<norm xml:id="u2" func="punct" pos="PUNCT" lemma="." norm=".">.</norm>
<norm xml:id="u3" func="obj" head="#u1" pos="N" norm="b">b</norm>
'''
        conllu = '''# sent_id = demo-s1
1\ta\ta\tVERB\tV\t_\t0\troot\t_\t_
2\t.\t.\tPUNCT\tPUNCT\t_\t1\tpunct\t_\t_
3\tb\tB\tNOUN\tN\t_\t1\tobl\t_\t_
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "demo" / "demo_TT"
            conllu_dir = root / "demo" / "demo_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)
            (tt_dir / "one.tt").write_text(tt, encoding="utf-8")
            (conllu_dir / "one.conllu").write_text(conllu, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(
            report["field_mismatch_categories"],
            {
                "func": {"different": 1, "missing_in_conllu": 0, "missing_in_tt": 0, "serialization_equivalent": 0},
                "head": {"different": 0, "missing_in_conllu": 0, "missing_in_tt": 1, "serialization_equivalent": 0},
                "lemma": {"different": 0, "missing_in_conllu": 0, "missing_in_tt": 1, "serialization_equivalent": 0},
                "norm": {"different": 0, "missing_in_conllu": 0, "missing_in_tt": 0, "serialization_equivalent": 0},
                "pos": {"different": 0, "missing_in_conllu": 0, "missing_in_tt": 0, "serialization_equivalent": 0},
            },
        )

    def test_xml_entity_escaping_in_conllu_is_serialization_equivalent_for_text_fields(self):
        tt = '''<meta corpus="demo">
<norm xml:id="u1" func="root" pos="N" lemma="a&lt;b&gt;" norm="a&lt;b&gt;">a&lt;b&gt;</norm>
'''
        conllu = '''# sent_id = demo-s1
1\ta&lt;b&gt;\ta&lt;b&gt;\tNOUN\tN\t_\t0\troot\t_\t_
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "demo" / "demo_TT"
            conllu_dir = root / "demo" / "demo_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)
            (tt_dir / "one.tt").write_text(tt, encoding="utf-8")
            (conllu_dir / "one.conllu").write_text(conllu, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["field_mismatch_counts"]["norm"], 1)
        self.assertEqual(report["field_mismatch_counts"]["lemma"], 1)
        self.assertEqual(report["field_mismatch_categories"]["norm"]["different"], 0)
        self.assertEqual(report["field_mismatch_categories"]["lemma"]["different"], 0)
        self.assertEqual(report["field_mismatch_categories"]["norm"]["serialization_equivalent"], 1)
        self.assertEqual(report["field_mismatch_categories"]["lemma"]["serialization_equivalent"], 1)


if __name__ == "__main__":
    unittest.main()
