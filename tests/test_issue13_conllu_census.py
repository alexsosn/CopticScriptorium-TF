import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-13" / "conllu_census.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue13_conllu_census", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load corpus census module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tt(norm: str = "a") -> str:
    return (
        '<meta corpus="demo">\n'
        '<norm_group norm_group="x">'
        f'<norm xml:id="u1" new_sent="true" func="root" norm="{norm}">{norm}</norm>'
        '</norm_group>\n'
    )


def conllu(form: str = "a") -> str:
    return f"# sent_id = s1\n1\t{form}\t_\t_\t_\t_\t0\troot\t_\t_\n"


class ConlluCorpusCensusContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = load_module()

    def test_census_pairs_direct_and_archive_records_and_classifies_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tt_dir = root / "demo" / "demo_TT"
            conllu_dir = root / "demo" / "demo_CONLLU"
            tt_dir.mkdir(parents=True)
            conllu_dir.mkdir(parents=True)

            (tt_dir / "valid.tt").write_text(tt(), encoding="utf-8")
            (conllu_dir / "valid.conllu").write_text(conllu(), encoding="utf-8")
            (tt_dir / "placeholder.tt").write_text(tt(), encoding="utf-8")
            (conllu_dir / "placeholder.conllu").write_text("\n", encoding="utf-8")
            (tt_dir / "malformed.tt").write_text(tt(), encoding="utf-8")
            (conllu_dir / "malformed.conllu").write_text(
                "# sent_id = s1\n1\ta\t_\t_\t_\t_\t-1\troot\t_\t_\n",
                encoding="utf-8",
            )

            archive = root / "arch" / "arch_TT.zip"
            archive.parent.mkdir()
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("arch_TT/zipped.tt", tt().encode("utf-8"))
            conllu_archive = root / "arch" / "arch_CONLLU.zip"
            with zipfile.ZipFile(conllu_archive, "w") as zf:
                zf.writestr("zipped.conllu", conllu().encode("utf-8"))

            report = self.census.build_report(root)

            self.assertEqual(report["tt_document_count"], 4)
            self.assertEqual(report["conllu_document_count"], 4)
            self.assertEqual(report["paired_document_count"], 4)
            self.assertEqual(report["valid_supplement_count"], 2)
            self.assertEqual(report["valid_supplement_word_count"], 2)
            self.assertEqual(report["unavailable_reasons"], {
                "malformed_conllu": 1,
                "placeholder": 1,
            })
            self.assertEqual(report["tt_only"], [])
            self.assertEqual(report["conllu_only"], [])
            self.assertEqual(report["unexpected_failures"], [])


if __name__ == "__main__":
    unittest.main()
