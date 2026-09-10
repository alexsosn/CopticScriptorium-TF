import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "identity_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_preference_eval", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load identity audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tt(root: Path, corpus: str, dataset: str, record: str, *, cts: str, parsing: str | None, pos: str = "N") -> None:
    directory = root / corpus / f"{dataset}_TT"
    directory.mkdir(parents=True, exist_ok=True)
    attrs = [f'corpus="{dataset}"', f'document_cts_urn="{cts}"', 'redundant="no"']
    if parsing is not None:
        attrs.append(f'parsing="{parsing}"')
    (directory / f"{record}.tt").write_text(
        "<meta " + " ".join(attrs) + ">\n"
        '<orig orig="Ⲁ">\n'
        f'<norm xml:id="u1" func="root" pos="{pos}" lemma="ⲁ" norm="ⲁ">Ⲁ</norm>\n'
        '</orig>\n',
        encoding="utf-8",
    )


class PreferenceEvaluationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_best_parsing_measures_unique_winner_tie_and_missing_quality(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Unique quality winner.
            write_tt(root, "a", "a", "one", cts="urn:cts:demo:one", parsing="gold")
            write_tt(root, "b", "b", "one", cts="urn:cts:demo:one", parsing="automatic")
            # Equal-quality tie.
            write_tt(root, "c", "c", "two", cts="urn:cts:demo:two", parsing="gold")
            write_tt(root, "d", "d", "two", cts="urn:cts:demo:two", parsing="gold")
            # Missing quality on every copy.
            write_tt(root, "e", "e", "three", cts="urn:cts:demo:three", parsing=None)
            write_tt(root, "f", "f", "three", cts="urn:cts:demo:three", parsing=None)

            report = self.audit.audit_upstream(root)
            pref = report["preference_evaluation"]
            self.assertEqual(pref["best_parsing_unique_winner_group_count"], 1)
            self.assertEqual(pref["best_parsing_tie_group_count"], 1)
            self.assertEqual(pref["best_parsing_missing_quality_group_count"], 1)
            one = next(g for g in report["duplicate_scholarly_identities"] if g["scholarly_id"] == "urn:cts:demo:one")
            self.assertEqual(one["best_parsing_candidates"], ["a/a:one"])
            self.assertFalse(one["best_parsing_tie"])
            two = next(g for g in report["duplicate_scholarly_identities"] if g["scholarly_id"] == "urn:cts:demo:two")
            self.assertEqual(two["best_parsing_candidates"], ["c/c:two", "d/d:two"])
            self.assertTrue(two["best_parsing_tie"])

    def test_source_preferred_is_only_eligible_for_core_equivalent_treebank_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Same bytes/core apart from path: eligible convenience-treebank duplicate.
            content = (
                '<meta corpus="source" document_cts_urn="urn:cts:demo:safe" redundant="no" parsing="gold">\n'
                '<orig orig="Ⲁ">\n'
                '<norm xml:id="u1" func="root" pos="N" lemma="ⲁ" norm="ⲁ">Ⲁ</norm>\n'
                '</orig>\n'
            )
            for corpus, dataset in (("source", "source"), ("coptic-treebank", "coptic.treebank")):
                directory = root / corpus / f"{dataset}_TT"
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "safe.tt").write_text(content, encoding="utf-8")
            # Alternate analysis: must not be source-preferred eligible.
            write_tt(root, "other", "other", "alt", cts="urn:cts:demo:alt", parsing="gold", pos="N")
            write_tt(root, "coptic-treebank", "coptic.treebank", "alt", cts="urn:cts:demo:alt", parsing="gold", pos="V")

            report = self.audit.audit_upstream(root)
            pref = report["preference_evaluation"]
            self.assertEqual(pref["source_preferred_eligible_group_count"], 1)
            self.assertEqual(pref["source_preferred_ineligible_group_count"], 1)
            safe = next(g for g in report["duplicate_scholarly_identities"] if g["scholarly_id"] == "urn:cts:demo:safe")
            self.assertEqual(safe["source_preferred_candidate"], "source/source:safe")
            alt = next(g for g in report["duplicate_scholarly_identities"] if g["scholarly_id"] == "urn:cts:demo:alt")
            self.assertIsNone(alt["source_preferred_candidate"])


if __name__ == "__main__":
    unittest.main()
