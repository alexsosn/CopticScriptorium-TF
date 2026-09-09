import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "conllu_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_conllu_audit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load conllu audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONLLU = '''# newdoc id = demo:one
# sent_id = demo-one_s0001
# text_en = Hello world
# text = ⲁ ⲃ
1-2	ⲁⲃ	_	_	_	_	_	_	_	_
1	ⲁ	LEMMA	VERB	V	Mood=Ind|VerbForm=Fin	0	root	_	Cxn=Existential|Orig=Ⲁ
2	ⲃ	B	NOUN	N	Gender=Masc	1	obj	1:obj	Entity=(person-Demo)|OrigLang=grc

# sent_id = demo-one_s0002
# text = ⲅ
1	ⲅ	G	ADV	ADV	_	0	root	_	_
'''


class ConlluAuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_audit_reports_structural_and_enrichment_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "demo" / "demo_CONLLU"
            directory.mkdir(parents=True)
            (directory / "one.conllu").write_text(CONLLU, encoding="utf-8")
            report = self.audit.audit_upstream(root)

        self.assertEqual(report["document_count"], 1)
        self.assertEqual(report["token_rows"], 3)
        self.assertEqual(report["multiword_rows"], 1)
        self.assertEqual(report["empty_node_rows"], 0)
        self.assertEqual(report["enhanced_deps_rows"], 1)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["upos_values"], {"ADV": 1, "NOUN": 1, "VERB": 1})
        self.assertEqual(report["xpos_values"], {"ADV": 1, "N": 1, "V": 1})
        self.assertEqual(report["feats_key_occurrences"], {"Gender": 1, "Mood": 1, "VerbForm": 1})
        self.assertEqual(report["feats_key_documents"], {"Gender": 1, "Mood": 1, "VerbForm": 1})
        self.assertEqual(
            report["misc_key_occurrences"],
            {"Cxn": 1, "Entity": 1, "Orig": 1, "OrigLang": 1},
        )
        self.assertEqual(
            report["misc_key_documents"],
            {"Cxn": 1, "Entity": 1, "Orig": 1, "OrigLang": 1},
        )
        self.assertEqual(
            report["comment_key_occurrences"],
            {"newdoc id": 1, "sent_id": 2, "text": 2, "text_en": 1},
        )

    def test_malformed_rows_are_reported_with_source_and_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "bad" / "bad_CONLLU"
            directory.mkdir(parents=True)
            (directory / "bad.conllu").write_text("1\ttoo\tfew\n", encoding="utf-8")
            report = self.audit.audit_upstream(root)
        self.assertEqual(report["document_count"], 1)
        self.assertEqual(report["token_rows"], 0)
        self.assertEqual(
            report["errors"],
            [
                {
                    "kind": "invalid_column_count",
                    "source": "bad/bad_CONLLU/bad.conllu",
                    "line": 1,
                    "columns": 3,
                }
            ],
        )

    def test_report_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "demo" / "demo_CONLLU"
            directory.mkdir(parents=True)
            (directory / "b.conllu").write_text(CONLLU, encoding="utf-8")
            (directory / "a.conllu").write_text(CONLLU, encoding="utf-8")
            first = self.audit.audit_upstream(root)
            second = self.audit.audit_upstream(root)
        self.assertEqual(first, second)
        self.assertEqual(
            self.audit.render_report_json(first),
            self.audit.render_report_json(second),
        )


if __name__ == "__main__":
    unittest.main()
