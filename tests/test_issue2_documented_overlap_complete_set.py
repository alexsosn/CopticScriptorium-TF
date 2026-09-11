import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "identity_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_documented_overlap_complete", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load identity audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_unrelated_tt(root: Path) -> None:
    directory = root / "other" / "other_TT"
    directory.mkdir(parents=True)
    (directory / "one.tt").write_text(
        '<meta corpus="other" document_cts_urn="urn:cts:demo:one" parsing="gold">\n'
        '<orig orig="Ⲁ">\n'
        '<norm xml:id="u1" func="root" pos="N" lemma="ⲁ" norm="ⲁ">Ⲁ</norm>\n'
        '</orig>\n',
        encoding="utf-8",
    )


class DocumentedOverlapCompleteSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_provenance_bound_rerun_reports_all_expected_pairs_when_documented_datasets_disappear(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_unrelated_tt(root)
            report = self.audit.audit_upstream(
                root,
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit="deadbeef",
            )

            missing = report["unmatched_documented_collection_overlaps"]
            self.assertEqual(len(missing), 36)
            self.assertTrue(all(item["missing_side"] == "both" for item in missing))
            self.assertIn(
                {
                    "expected_left": "sahidica.mark/sahidica.mark:Mark_01",
                    "expected_right": "sahidica.nt/sahidica.nt:41_Mark_01",
                    "missing_side": "both",
                },
                missing,
            )
            self.assertIn(
                {
                    "expected_left": "sahidic.ruth/sahidic.ruth:Ruth_04",
                    "expected_right": "sahidic.ot/sahidic.ot:08_Ruth_04",
                    "missing_side": "both",
                },
                missing,
            )


if __name__ == "__main__":
    unittest.main()
