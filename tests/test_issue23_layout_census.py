import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-13" / "parser_census.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue23_parser_census", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load parser census from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LayoutCensusContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = load_module()

    def test_report_counts_all_layout_events_as_positionable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "demo" / "demo_TT"
            directory.mkdir(parents=True)
            (directory / "one.tt").write_text(
                '<meta corpus="demo">\n'
                '<lb_n lb_n="before">\n'
                '<norm_group norm_group="x">'
                '<norm xml:id="u1" new_sent="true" func="root" norm="ab">'
                'a<cb_n cb_n="inside">b'
                '</norm>'
                '</norm_group>\n'
                '<pb_xml_id pb_xml_id="after">\n',
                encoding="utf-8",
            )

            report = self.census.build_report(root)

        self.assertEqual(report["layout_event_count"], 3)
        self.assertEqual(report["positionable_layout_event_count"], 3)
        self.assertEqual(report["invalid_layout_positions"], [])


if __name__ == "__main__":
    unittest.main()
