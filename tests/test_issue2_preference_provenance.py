import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "preference_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_preference_provenance", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load preference audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PreferenceProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_preference_report_preserves_identity_report_source_provenance(self):
        provenance = {
            "repository": "CopticScriptorium/corpora",
            "commit": "3ac067f1709a0012daf39ea8da2fac79980176a5",
        }
        report = self.audit.evaluate_identity_report(
            {
                "source_provenance": provenance,
                "duplicate_scholarly_identities": [],
            }
        )
        self.assertEqual(report["source_provenance"], provenance)

    def test_missing_source_provenance_is_explicit_not_invented(self):
        report = self.audit.evaluate_identity_report(
            {"duplicate_scholarly_identities": []}
        )
        self.assertIsNone(report["source_provenance"])


if __name__ == "__main__":
    unittest.main()
