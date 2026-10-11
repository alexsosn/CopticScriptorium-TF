"""#109 RED-first observational parity and source-compatible memory phase contract."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric

from copticscriptorium_tf.converter import convert_source_tree
import importlib.util
from unittest.mock import patch


TT = (
    '<meta corpus="small" document_cts_urn="urn:cts:copticLit:small.test" title="Small">'
    '<norm_group norm_group="a"><norm xml:id="u1" new_sent="true"'
    ' func="root" pos="N" norm="a">a</norm>'
    '<norm xml:id="u2" func="obj" head="#u1" pos="N" norm="b">'
    '<morph morph="b">b</morph></norm></norm_group>'
)
PIN = "d" * 40
PHASES = (
    "start", "parsed_and_supplemented", "graph_built",
    "models_released", "writer_complete", "reload_complete",
)


def _source_tree(root: Path) -> None:
    folder = root / "small" / "small_TT"
    folder.mkdir(parents=True)
    (folder / "test.tt").write_text(TT, encoding="utf-8")


def _research_smoke_module():
    """Load the real research runner without invoking its CLI entry point."""
    location = (
        Path(__file__).resolve().parents[1]
        / "research/issue-16/full_converter_smoke.py"
    )
    spec = importlib.util.spec_from_file_location("issue109_smoke", location)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _small_fixture_reload(tf_dir: Path, result):
    """Exercise real TF reload; full-corpus-only edge gates run separately in CI."""
    api = Fabric(locations=[str(tf_dir)], silent="deep").load(
        "value dependency_head", silent="deep",
    )
    assert api and api.F.otype.maxSlot == 2
    assert len(api.F.otype.s("morph")) == 1
    assert tuple(api.E.dependency_head.f(2)) == (1,)
    assert api.F.otype.maxNode - api.F.otype.maxSlot == result.nodes
    return {"reload_slots": api.F.otype.maxSlot, "reload_nodes": result.nodes}


class PhaseMemoryProfileContractTests(unittest.TestCase):
    def test_opt_in_callback_has_explicit_phase_boundaries_and_identical_tf_bytes(self):
        seen = []
        with TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "source"
            _source_tree(source)
            original = convert_source_tree(
                source, base / "normal",
                upstream_repository="fixture/repo", upstream_commit=PIN,
            )
            profiled = convert_source_tree(
                source, base / "measured",
                upstream_repository="fixture/repo", upstream_commit=PIN,
                phase_probe=seen.append,
            )
            self.assertEqual(seen, list(PHASES[:-1]))
            self.assertEqual(
                (original.slots, original.nodes, original.edges, original.tf_bytes),
                (profiled.slots, profiled.nodes, profiled.edges, profiled.tf_bytes),
            )
            files0 = {p.name: p.read_bytes() for p in (base / "normal").glob("*.tf")}
            files1 = {p.name: p.read_bytes() for p in (base / "measured").glob("*.tf")}
            self.assertEqual(files0, files1, "Memory profiler changed actual TF serialization")
            api = Fabric(locations=[str(base / "measured")], silent="deep").load(
                "value dependency_head", silent="deep",
            )
            self.assertEqual(api.F.otype.maxSlot, 2)
            self.assertEqual(api.F.value.v(api.F.otype.s("morph")[0]), "b")
            self.assertEqual(tuple(api.E.dependency_head.f(2)), (1,))

    def test_smoke_opt_in_reports_phase_rss_and_post_reload(self):
        smoke = _research_smoke_module()
        with TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "source"
            _source_tree(source)
            report = base / "report.json"
            with patch.object(smoke, "_reload_and_check", new=_small_fixture_reload):
                status = smoke.main([
                    str(source), "--work-root", str(base / "work"),
                    "--output", str(report), "--profile-memory",
                ])
            self.assertEqual(status, 0)
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["source_records"], 1)
            self.assertEqual(data["slots"], 2)
            profile = data["memory_profile"]
            self.assertEqual([row["phase"] for row in profile], list(PHASES))
            for row in profile:
                self.assertIsInstance(row["elapsed_seconds"], (int, float))
                self.assertGreaterEqual(row["elapsed_seconds"], 0)
                self.assertIsInstance(row["peak_rss_mb"], (int, float))
                self.assertGreaterEqual(row["peak_rss_mb"], 0)
                self.assertTrue(
                    row["current_rss_mb"] is None
                    or isinstance(row["current_rss_mb"], (int, float))
                )
            self.assertTrue((base / "work/tf/otype.tf").exists())

    def test_default_smoke_report_has_no_memory_profile_key(self):
        smoke = _research_smoke_module()
        with TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "source"
            _source_tree(source)
            report = base / "report.json"
            with patch.object(smoke, "_reload_and_check", new=_small_fixture_reload):
                status = smoke.main([
                    str(source), "--work-root", str(base / "work"),
                    "--output", str(report),
                ])
            self.assertEqual(status, 0)
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertNotIn("memory_profile", data)
            self.assertIn("peak_rss_mb", data)


if __name__ == "__main__":
    unittest.main()
