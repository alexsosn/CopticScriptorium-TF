"""Issue #16 end-to-end converter contract.

The fixture tests converter behavior only. They do not certify upstream corpus data.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tf.fabric import Fabric


DIRECT_TT = """<meta corpus="alpha" document_cts_urn="urn:cts:copticLit:fixture.a" title="Alpha">
<norm_group norm_group="ab"><orig orig="ab">
<translation translation="English A">
<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a<entity entity="person" head_tok="#u1" identity="Person">x</entity></norm>
<norm xml:id="u2" func="dep" head="#u1" pos="V" lemma="b" norm="b">b</norm>
</translation>
</orig></norm_group>
"""

ARCHIVE_TT = """<meta corpus="beta" document_cts_urn="urn:cts:copticLit:fixture.b" title="Beta">
<norm_group norm_group="c"><norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="c" norm="c">c</norm></norm_group>
"""


def _source_tree(root: Path) -> None:
    direct = root / "alpha" / "alpha_TT"
    direct.mkdir(parents=True)
    (direct / "a.tt").write_text(DIRECT_TT, encoding="utf-8")

    archive_dir = root / "beta"
    archive_dir.mkdir()
    with zipfile.ZipFile(archive_dir / "beta_TT.zip", "w") as archive:
        archive.writestr("beta_TT/b.tt", ARCHIVE_TT.encode("utf-8"))


def _load_tf(path: Path):
    api = Fabric(locations=[str(path)], silent="deep").load(
        "source_record_id source_word_ordinal norm lemma pos meta_title "
        "dependency_head entity_head own_text",
        silent="deep",
    )
    if api is False or api is None:
        raise AssertionError("generated Text-Fabric failed clean reload")
    return api


class ConverterContractTests(unittest.TestCase):
    def test_one_public_api_converts_direct_and_zip_sources_to_reloadable_native_tf(self):
        from copticscriptorium_tf.converter import convert_source_tree

        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            _source_tree(root)
            destination = Path(temporary) / "tf"

            result = convert_source_tree(
                root,
                destination,
                upstream_repository="fixture/repo",
                upstream_commit="deadbeef",
            )

            self.assertEqual(result.source_records, 2)
            self.assertEqual(result.slots, 3)
            self.assertGreater(result.nodes, 0)
            self.assertGreater(result.edges, 0)
            self.assertEqual(result.output_path, destination)
            self.assertGreater(result.tf_files, 0)
            self.assertGreater(result.tf_bytes, 0)
            self.assertGreaterEqual(result.peak_rss_mb, 0)
            self.assertGreaterEqual(result.parse_seconds, 0)
            self.assertGreaterEqual(result.graph_seconds, 0)
            self.assertGreaterEqual(result.write_seconds, 0)

            feature_names = {path.stem for path in destination.glob("*.tf")}
            self.assertFalse({name for name in feature_names if name.endswith("_json")})

            api = _load_tf(destination)
            self.assertEqual(api.F.otype.maxSlot, 3)
            alpha = api.T.nodeFromSection(("alpha/alpha:a",))
            beta = api.T.nodeFromSection(("beta/beta:b",))
            self.assertIsNotNone(alpha)
            self.assertIsNotNone(beta)
            self.assertEqual(api.F.meta_title.v(alpha), "Alpha")
            self.assertEqual(api.F.meta_title.v(beta), "Beta")
            self.assertEqual(tuple(api.E.dependency_head.f(2)), (1,))
            entity = api.F.otype.s("entity")[0]
            self.assertEqual(tuple(api.E.entity_head.f(entity)), (1,))
            translation = api.F.otype.s("translation")[0]
            self.assertEqual(api.T.text(translation), "English A")

    def test_converter_fails_closed_for_invalid_empty_input_and_existing_destination(self):
        from copticscriptorium_tf.converter import convert_source_tree

        with TemporaryDirectory() as temporary:
            base = Path(temporary)

            empty_root = base / "empty"
            empty_root.mkdir()
            empty_destination = base / "empty-output"
            with self.assertRaisesRegex(ValueError, "no supported TT source records"):
                convert_source_tree(
                    empty_root,
                    empty_destination,
                    upstream_repository="fixture/repo",
                    upstream_commit="deadbeef",
                )
            self.assertFalse(empty_destination.exists())

            invalid_root = base / "invalid"
            nested = invalid_root / "alpha" / "alpha_TT" / "nested"
            nested.mkdir(parents=True)
            (nested / "a.tt").write_text(DIRECT_TT, encoding="utf-8")
            destination = base / "invalid-output"
            with self.assertRaisesRegex(ValueError, "directory member layout"):
                convert_source_tree(
                    invalid_root,
                    destination,
                    upstream_repository="fixture/repo",
                    upstream_commit="deadbeef",
                )
            self.assertFalse(destination.exists())

            valid_root = base / "valid"
            valid_root.mkdir()
            _source_tree(valid_root)
            existing = base / "existing-output"
            existing.mkdir()
            sentinel = existing / "keep.txt"
            sentinel.write_text("do not overwrite", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "overwrite"):
                convert_source_tree(
                    valid_root,
                    existing,
                    upstream_repository="fixture/repo",
                    upstream_commit="deadbeef",
                )
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not overwrite")
            self.assertEqual(sorted(path.name for path in existing.iterdir()), ["keep.txt"])

    def test_module_cli_writes_operational_summary_not_certification_verdict(self):
        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "source"
            root.mkdir()
            _source_tree(root)
            destination = base / "tf"
            summary = base / "summary.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "copticscriptorium_tf.converter",
                    str(root),
                    str(destination),
                    "--upstream-repository",
                    "fixture/repo",
                    "--upstream-commit",
                    "deadbeef",
                    "--summary",
                    str(summary),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertNotIn("RuntimeWarning", completed.stderr)
            report = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(report["source_records"], 2)
            self.assertEqual(report["slots"], 3)
            self.assertEqual(Path(report["output_path"]), destination)
            serialized = json.dumps(report, sort_keys=True).casefold()
            self.assertNotIn("certif", serialized)
            self.assertNotIn("expected_count", serialized)
            self.assertTrue((destination / "otype.tf").is_file())
            self.assertTrue((destination / "oslots.tf").is_file())


if __name__ == "__main__":
    unittest.main()
