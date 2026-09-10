import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "identity_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_documented_overlap", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load identity audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tt(
    root: Path,
    corpus: str,
    dataset: str,
    record: str,
    *,
    cts: str,
    pos: str = "N",
    norm: str = "ⲁ",
) -> None:
    directory = root / corpus / f"{dataset}_TT"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{record}.tt").write_text(
        f'<meta corpus="{dataset}" document_cts_urn="{cts}" redundant="no" parsing="gold">\n'
        '<orig orig="Ⲁ">\n'
        f'<norm xml:id="u1" func="root" pos="{pos}" lemma="ⲁ" norm="{norm}">Ⲁ</norm>\n'
        '</orig>\n',
        encoding="utf-8",
    )


class DocumentedCollectionOverlapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_mark_book_and_aggregate_are_related_without_collapsing_cts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(
                root,
                "sahidica.mark",
                "sahidica.mark",
                "Mark_01",
                cts="urn:cts:copticLit:nt.mark.sahidica_ed:1",
                pos="N",
            )
            write_tt(
                root,
                "sahidica.nt",
                "sahidica.nt",
                "41_Mark_01",
                cts="urn:cts:copticLit:nt.mark.sahidica:1",
                pos="V",
            )

            report = self.audit.audit_upstream(root)
            self.assertEqual(report["documented_collection_overlap_count"], 1)
            self.assertEqual(report["unmatched_documented_collection_overlaps"], [])
            overlap = report["documented_collection_overlaps"][0]
            self.assertEqual(overlap["relation"], "book_aggregate")
            self.assertEqual(overlap["classification"], "alternate_analysis")
            self.assertFalse(overlap["same_scholarly_id"])
            self.assertEqual(
                overlap["left_scholarly_id"],
                "urn:cts:copticLit:nt.mark.sahidica_ed:1",
            )
            self.assertEqual(
                overlap["right_scholarly_id"],
                "urn:cts:copticLit:nt.mark.sahidica:1",
            )
            self.assertEqual(
                report["documented_collection_overlap_class_counts"]["alternate_analysis"],
                1,
            )

    def test_documented_overlap_missing_counterpart_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(
                root,
                "sahidic.ruth",
                "sahidic.ruth",
                "Ruth_04",
                cts="urn:cts:copticLit:ot.ruth.coptot_ed:4",
            )

            report = self.audit.audit_upstream(root)
            self.assertEqual(report["documented_collection_overlap_count"], 0)
            self.assertEqual(len(report["unmatched_documented_collection_overlaps"]), 1)
            missing = report["unmatched_documented_collection_overlaps"][0]
            self.assertEqual(missing["left"], "sahidic.ruth/sahidic.ruth:Ruth_04")
            self.assertEqual(missing["expected_right"], "sahidic.ot/sahidic.ot:08_Ruth_04")

    def test_similar_cts_suffix_outside_documented_datasets_does_not_infer_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tt(
                root,
                "other",
                "other",
                "one",
                cts="urn:cts:copticLit:work.demo_ed:1",
            )
            write_tt(
                root,
                "aggregate",
                "aggregate",
                "one",
                cts="urn:cts:copticLit:work.demo:1",
            )

            report = self.audit.audit_upstream(root)
            self.assertEqual(report["documented_collection_overlap_count"], 0)
            self.assertEqual(report["documented_collection_overlaps"], [])
            self.assertEqual(report["unmatched_documented_collection_overlaps"], [])


if __name__ == "__main__":
    unittest.main()
