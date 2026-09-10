import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "identity_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_identity_witness", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load identity audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tt(
    root: Path,
    corpus: str,
    record: str,
    *,
    cts: str,
    redundant: str = "no",
    witness: str | None = None,
) -> None:
    directory = root / corpus / f"{corpus}_TT"
    directory.mkdir(parents=True, exist_ok=True)
    attrs = [
        f'corpus="{corpus}"',
        f'document_cts_urn="{cts}"',
        f'redundant="{redundant}"',
        'parsing="gold"',
    ]
    if witness is not None:
        attrs.append(f'witness="{witness}"')
    text = (
        "<meta " + " ".join(attrs) + ">\n"
        '<orig orig="Ⲁ">\n'
        '<norm xml:id="u1" func="root" pos="N" lemma="ⲁ" norm="ⲁ">Ⲁ</norm>\n'
        "</orig>\n"
    )
    (directory / f"{record}.tt").write_text(text, encoding="utf-8")


class WitnessTypeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_free_text_witness_is_preserved_but_not_treated_as_broken_cts_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prose = "Parallel witness in MONB.XO 108-115; not published by Coptic Scriptorium"
            write_tt(
                root,
                "demo",
                "one",
                cts="urn:cts:demo:one",
                redundant="yes",
                witness=prose,
            )

            report = self.audit.audit_upstream(root)
            self.assertEqual(report["witness_relation_count"], 1)
            relation = report["witness_relations"][0]
            self.assertEqual(relation["witness"], prose)
            self.assertEqual(relation["witness_kind"], "free_text")
            self.assertIsNone(relation["witness_resolved"])
            self.assertEqual(relation["witness_cts_targets"], [])
            self.assertEqual(report["unresolved_witness_relations"], [])
            redundant = report["redundant_records"][0]
            self.assertEqual(redundant["witness_kind"], "free_text")
            self.assertIsNone(redundant["witness_resolved"])

    def test_cts_witness_relation_is_measured_even_when_record_is_not_redundant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = "urn:cts:demo:target"
            write_tt(root, "target", "target", cts=target)
            write_tt(
                root,
                "source",
                "source",
                cts="urn:cts:demo:source",
                redundant="no",
                witness=target,
            )

            report = self.audit.audit_upstream(root)
            self.assertEqual(report["redundant_record_count"], 0)
            self.assertEqual(report["witness_relation_count"], 1)
            relation = report["witness_relations"][0]
            self.assertEqual(relation["witness_kind"], "cts")
            self.assertTrue(relation["witness_resolved"])
            self.assertEqual(relation["witness_cts_targets"], [target])
            self.assertEqual(relation["resolved_witness_cts_targets"], [target])
            self.assertEqual(relation["unresolved_witness_cts_targets"], [])
            self.assertEqual(report["unresolved_witness_relations"], [])

    def test_free_text_witness_extracts_embedded_cts_targets_without_rewriting_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            known = "urn:cts:demo:known"
            absent = "urn:cts:demo:absent"
            write_tt(root, "known", "known", cts=known)
            prose = f"Beginning parallels {known}. End parallels {absent}, not yet published."
            write_tt(
                root,
                "source",
                "source",
                cts="urn:cts:demo:source",
                redundant="yes",
                witness=prose,
            )

            report = self.audit.audit_upstream(root)
            relation = next(
                item for item in report["witness_relations"]
                if item["source_record_id"].endswith(":source")
            )
            self.assertEqual(relation["witness"], prose)
            self.assertEqual(relation["witness_kind"], "free_text")
            self.assertIsNone(relation["witness_resolved"])
            self.assertEqual(relation["witness_cts_targets"], [known, absent])
            self.assertEqual(relation["resolved_witness_cts_targets"], [known])
            self.assertEqual(relation["unresolved_witness_cts_targets"], [absent])
            self.assertEqual(
                report["unresolved_witness_relations"],
                [
                    {
                        "source_record_id": "source/source:source",
                        "scholarly_id": "urn:cts:demo:source",
                        "witness": prose,
                        "target": absent,
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
