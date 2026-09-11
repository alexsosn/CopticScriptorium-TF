import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "identity_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_identity_cli", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load identity audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IdentityAuditCliContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_main_writes_deterministic_provenance_bound_json_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "upstream"
            root.mkdir()
            output = Path(tmp) / "identity.json"
            repository = "CopticScriptorium/corpora"
            commit = "3ac067f1709a0012daf39ea8da2fac79980176a5"

            self.assertEqual(
                self.audit.main(
                    [
                        str(root),
                        "--output",
                        str(output),
                        "--upstream-repository",
                        repository,
                        "--upstream-commit",
                        commit,
                    ]
                ),
                0,
            )
            self.assertTrue(output.is_file())
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["document_count"], 0)
            self.assertEqual(report["records"], [])
            self.assertEqual(
                report["source_provenance"],
                {
                    "repository": repository,
                    "commit": commit,
                },
            )
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                self.audit.render_report_json(report),
            )


if __name__ == "__main__":
    unittest.main()
