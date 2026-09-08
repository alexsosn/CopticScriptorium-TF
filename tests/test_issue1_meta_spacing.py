import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-1" / "semantic_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue1_semantic_spacing", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load semantic audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MetaSpacingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_source_meta_allows_whitespace_around_equals(self):
        parsed = self.audit.scan_meta_line(
            '<meta title="A" msItem_title ="B" objectType= "codex" note = "C">'
        )
        self.assertEqual(
            parsed,
            {
                "attributes": {
                    "title": "A",
                    "msItem_title": "B",
                    "objectType": "codex",
                    "note": "C",
                },
                "duplicates": {},
            },
        )


if __name__ == "__main__":
    unittest.main()
