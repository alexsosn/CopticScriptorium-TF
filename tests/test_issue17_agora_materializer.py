"""RED-first user-local/Agora materialization contracts for issue #17.

No Agora machinery is reimplemented here: its existing output root is deliberately
created before the adapter runs, and the manifest contract is checked separately.
"""
from __future__ import annotations

import json
from pathlib import Path
import socket
import tempfile
import tomllib
import unittest
from unittest.mock import patch
import zipfile

from tf.fabric import Fabric

from copticscriptorium_tf.converter import convert_source_tree


ROOT = Path(__file__).resolve().parents[1]
REVISION = "3ac067f1709a0012daf39ea8da2fac79980176a5"
DIRECT_TT = (
    '<meta corpus="alpha" document_cts_urn="urn:cts:copticLit:fixture.a" title="Alpha">'
    '<norm_group norm_group="a"><norm xml:id="u1" new_sent="true" '
    'func="root" pos="N" lemma="a" norm="a">a</norm></norm_group>'
)
ARCHIVE_TT = (
    '<meta corpus="beta" document_cts_urn="urn:cts:copticLit:fixture.b" title="Beta">'
    '<norm_group norm_group="b"><norm xml:id="u1" new_sent="true" '
    'func="root" pos="N" lemma="b" norm="b">b</norm></norm_group>'
)


def _sources(root: Path, *, direct: bool, archive: bool) -> None:
    root.mkdir()
    if direct:
        directory = root / "alpha" / "alpha_TT"
        directory.mkdir(parents=True)
        (directory / "a.tt").write_text(DIRECT_TT, encoding="utf-8")
    if archive:
        corpus = root / "beta"
        corpus.mkdir()
        with zipfile.ZipFile(corpus / "beta_TT.zip", "w") as bundle:
            bundle.writestr("beta_TT/b.tt", ARCHIVE_TT.encode("utf-8"))


class AgoraManifestContractTests(unittest.TestCase):
    def test_manifest_is_compatible_with_existing_agora_v1_contract(self) -> None:
        manifest = json.loads((ROOT / "agora.materializer.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["plugin"]["id"], "copticscriptorium-tf")
        self.assertEqual(manifest["plugin"]["repository"], "alexsosn/CopticScriptorium-TF")
        self.assertEqual(len(manifest["materializers"]), 1)
        item = manifest["materializers"][0]
        self.assertEqual(item["id"], "copticscriptorium-text-fabric")
        self.assertEqual({x["type"] for x in item["acquisition"]}, {"git", "user-local"})
        git = next(x for x in item["acquisition"] if x["type"] == "git")
        self.assertEqual(git["ref"], REVISION)
        self.assertEqual(git["url"], "https://github.com/CopticScriptorium/corpora.git")
        self.assertEqual(item["input"]["required_globs"], ["*/*_TT*"])
        self.assertFalse(item["input"]["allow_symlinks"])
        self.assertEqual(item["execution"]["type"], "python-module")
        self.assertEqual(item["execution"]["module"], "copticscriptorium_tf.agora")
        self.assertEqual(item["execution"]["network"], "deny")
        self.assertIn("{source}", item["execution"]["args"])
        self.assertIn("{output}", item["execution"]["args"])
        self.assertIn("{source_revision}", item["execution"]["args"])
        self.assertEqual(item["output"]["format"], "text-fabric")
        self.assertEqual(set(item["output"]["required_paths"]), {
            "tf/otype.tf", "tf/oslots.tf", "tf/otext.tf", "conversion-summary.json",
        })

    def test_python_package_is_installable_by_agora(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project["name"], "copticscriptorium-tf")
        self.assertIn("text-fabric==13.1.0", project["dependencies"])


class AgoraAdapterTests(unittest.TestCase):
    def test_existing_empty_output_converts_mixed_source_and_matches_direct_tf_bytes(self) -> None:
        from copticscriptorium_tf.agora import main

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            _sources(source, direct=True, archive=True)
            output = root / "agora-output"
            output.mkdir()  # Agora creates the private staging output before execution.
            with patch.object(socket, "create_connection", side_effect=AssertionError("network used")):
                self.assertEqual(main([str(source), str(output), "--source-revision", REVISION]), 0)
            self.assertEqual(
                {p.name for p in output.iterdir()}, {"tf", "conversion-summary.json"},
            )
            report = json.loads((output / "conversion-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(report["output_path"], "tf")
            self.assertEqual(report["source_records"], 2)
            self.assertEqual(report["upstream_commit"], REVISION)
            self.assertNotIn(str(output), (output / "conversion-summary.json").read_text())
            api = Fabric(locations=[str(output / "tf")], silent="deep").load(
                "norm lemma pos source_record_id", silent="deep",
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 2)
            self.assertEqual({api.F.norm.v(i) for i in (1, 2)}, {"a", "b"})
            direct = convert_source_tree(
                source, root / "direct", upstream_repository="CopticScriptorium/corpora",
                upstream_commit=REVISION,
            )
            self.assertEqual(direct.source_records, 2)
            self.assertEqual(
                {p.name: p.read_bytes() for p in (output / "tf").glob("*.tf") if p.is_file()},
                {p.name: p.read_bytes() for p in (root / "direct").glob("*.tf") if p.is_file()},
            )

    def test_zip_only_local_source_without_git_revision_is_explicitly_unversioned(self) -> None:
        from copticscriptorium_tf.agora import main

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            _sources(source, direct=False, archive=True)
            output = root / "output"
            output.mkdir()
            self.assertEqual(main([str(source), str(output), "--source-revision", ""]), 0)
            report = json.loads((output / "conversion-summary.json").read_text())
            self.assertEqual(report["upstream_commit"], "unversioned-local")
            self.assertEqual(report["source_records"], 1)
            self.assertTrue((output / "tf" / "otype.tf").is_file())

    def test_bad_input_and_nonempty_output_fail_without_published_data(self) -> None:
        from copticscriptorium_tf.agora import main

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            empty = root / "source"
            empty.mkdir()
            output = root / "output"
            output.mkdir()
            self.assertNotEqual(main([str(empty), str(output), "--source-revision", REVISION]), 0)
            self.assertEqual(list(output.iterdir()), [])
            source = root / "valid"
            _sources(source, direct=True, archive=False)
            sentinel = output / "do-not-overwrite"
            sentinel.write_text("kept")
            self.assertNotEqual(main([str(source), str(output), "--source-revision", REVISION]), 0)
            self.assertEqual(list(output.iterdir()), [sentinel])
            self.assertFalse((output / "conversion-summary.json").exists())


if __name__ == "__main__":
    unittest.main()
