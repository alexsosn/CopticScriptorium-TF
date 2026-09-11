import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-2" / "identity_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue2_identity_audit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load identity audit module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tt(
    *,
    cts: str | None,
    norm: str = "ⲁ",
    orig: str = "Ⲁ",
    pos: str = "N",
    func: str = "root",
    head: str | None = None,
    redundant: str = "no",
    witness: str | None = None,
    extra_meta: str = "",
    extra_markup: str = "",
) -> str:
    attrs = [
        'corpus="demo"',
        'title="Demo"',
        f'redundant="{redundant}"',
        'segmentation="gold"',
        'tagging="gold"',
        'parsing="gold"',
        'entities="gold"',
        'identities="gold"',
    ]
    if cts is not None:
        attrs.append(f'document_cts_urn="{cts}"')
    if witness is not None:
        attrs.append(f'witness="{witness}"')
    if extra_meta:
        attrs.append(extra_meta)
    head_attr = f' head="{head}"' if head is not None else ""
    return (
        "<meta " + " ".join(attrs) + ">\n"
        f'<orig orig="{orig}">\n'
        f'<norm xml:id="u1" func="{func}"{head_attr} pos="{pos}" lemma="ⲁ" norm="{norm}">\n'
        f"{orig}\n"
        "</norm>\n"
        "</orig>\n"
        f"{extra_markup}"
    )


def write_direct(root: Path, corpus: str, dataset: str, record: str, content: str) -> Path:
    directory = root / corpus / f"{dataset}_TT"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record}.tt"
    path.write_text(content, encoding="utf-8")
    return path


def write_archive(root: Path, corpus: str, dataset: str, record: str, content: bytes) -> Path:
    directory = root / corpus
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{dataset}_TT.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{dataset}_TT/{record}.tt", content)
    return path


class IdentityAuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_classifies_byte_identical_same_cts_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = tt(cts="urn:cts:demo:one")
            write_direct(root, "source", "source", "one", content)
            write_direct(root, "copy", "copy", "one", content)

            report = self.audit.audit_upstream(root)
            group = report["duplicate_scholarly_identities"][0]
            self.assertEqual(group["scholarly_id"], "urn:cts:demo:one")
            self.assertEqual(group["classification"], "byte_identical")
            self.assertEqual(group["copy_count"], 2)
            self.assertEqual(group["pair_classifications"][0]["classification"], "byte_identical")

    def test_classifies_core_identical_source_variant_across_directory_and_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cts = "urn:cts:demo:enriched"
            source = tt(cts=cts)
            enriched = tt(
                cts=cts,
                extra_meta='Arabic_translation="Translator"',
                extra_markup='<arabic arabic="translation">translation</arabic>\n',
            )
            write_direct(root, "source", "source", "one", source)
            write_archive(root, "coptic-treebank", "coptic.treebank", "one", enriched.encode("utf-8"))

            report = self.audit.audit_upstream(root)
            group = report["duplicate_scholarly_identities"][0]
            self.assertEqual(group["classification"], "core_identical_source_variant")
            self.assertNotEqual(group["records"][0]["raw_sha256"], group["records"][1]["raw_sha256"])
            self.assertEqual(
                {record["packaging"] for record in group["records"]},
                {"directory", "archive"},
            )
            self.assertNotEqual(
                group["records"][0]["enrichment"],
                group["records"][1]["enrichment"],
            )

    def test_classifies_same_text_different_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cts = "urn:cts:demo:analysis"
            write_direct(root, "a", "a", "one", tt(cts=cts, pos="N"))
            write_direct(root, "b", "b", "one", tt(cts=cts, pos="V"))

            group = self.audit.audit_upstream(root)["duplicate_scholarly_identities"][0]
            self.assertEqual(group["classification"], "alternate_analysis")
            self.assertEqual(
                len({record["normalized_text_sha256"] for record in group["records"]}),
                1,
            )
            self.assertEqual(
                len({record["analysis_sha256"] for record in group["records"]}),
                2,
            )

    def test_classifies_textual_divergence_before_analysis_differences(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cts = "urn:cts:demo:text"
            write_direct(root, "a", "a", "one", tt(cts=cts, norm="ⲁ", pos="N"))
            write_direct(root, "b", "b", "one", tt(cts=cts, norm="ⲃ", pos="V"))

            group = self.audit.audit_upstream(root)["duplicate_scholarly_identities"][0]
            self.assertEqual(group["classification"], "textual_divergence")

    def test_missing_cts_is_preserved_as_physical_record_not_grouped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_direct(root, "a", "a", "missing", tt(cts=None))

            report = self.audit.audit_upstream(root)
            self.assertEqual(report["document_count"], 1)
            self.assertEqual(report["scholarly_identity_count"], 0)
            self.assertEqual(report["duplicate_scholarly_identities"], [])
            self.assertEqual(len(report["missing_scholarly_identity_records"]), 1)
            self.assertIn("a/a:missing", report["missing_scholarly_identity_records"][0]["source_record_id"])

    def test_redundant_witness_relation_is_independent_and_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = "urn:cts:demo:target"
            write_direct(root, "a", "a", "target", tt(cts=target))
            write_direct(
                root,
                "b",
                "b",
                "witness",
                tt(
                    cts="urn:cts:demo:witness",
                    redundant="yes",
                    witness=target,
                ),
            )

            report = self.audit.audit_upstream(root)
            self.assertEqual(report["redundant_record_count"], 1)
            redundant = report["redundant_records"][0]
            self.assertEqual(redundant["witness"], target)
            self.assertTrue(redundant["witness_resolved"])
            self.assertEqual(report["unresolved_witness_relations"], [])

    def test_unresolved_witness_relation_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_direct(
                root,
                "b",
                "b",
                "witness",
                tt(
                    cts="urn:cts:demo:witness",
                    redundant="yes",
                    witness="urn:cts:demo:absent",
                ),
            )

            report = self.audit.audit_upstream(root)
            self.assertEqual(len(report["unresolved_witness_relations"]), 1)
            self.assertEqual(
                report["unresolved_witness_relations"][0]["witness"],
                "urn:cts:demo:absent",
            )

    def test_case_insensitive_source_record_collision_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_direct(root, "a", "a", "One", tt(cts="urn:cts:demo:one"))
            write_direct(root, "a", "a", "one", tt(cts="urn:cts:demo:two"))

            with self.assertRaisesRegex(ValueError, "source-record.*collision"):
                self.audit.audit_upstream(root)

    def test_invalid_utf8_fails_closed_for_direct_and_archive_sources(self):
        for packaging in ("directory", "archive"):
            with self.subTest(packaging=packaging), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                invalid = b'<meta document_cts_urn="urn:cts:demo:bad">\n\xff\n'
                if packaging == "directory":
                    directory = root / "a" / "a_TT"
                    directory.mkdir(parents=True)
                    (directory / "bad.tt").write_bytes(invalid)
                else:
                    write_archive(root, "a", "a", "bad", invalid)

                with self.assertRaises(UnicodeDecodeError):
                    self.audit.audit_upstream(root)

    def test_report_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_direct(root, "z", "z", "two", tt(cts="urn:cts:demo:two"))
            write_direct(root, "a", "a", "one", tt(cts="urn:cts:demo:one"))
            first = self.audit.audit_upstream(root)
            second = self.audit.audit_upstream(root)
            self.assertEqual(first, second)
            self.assertEqual(
                self.audit.render_report_json(first),
                self.audit.render_report_json(second),
            )


if __name__ == "__main__":
    unittest.main()
