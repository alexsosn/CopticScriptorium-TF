"""RED-first converter memory profiling (not a performance claim)."""
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from test_issue16_converter import _source_tree, REVISION


class MemoryPhaseResearchTests(TestCase):
    def test_current_linux_rss_is_not_cumulative_peak(self):
        from copticscriptorium_tf.converter import _parse_linux_vmrss_kib
        valid = "Name:\tpython\nVmPeak:\t128000 kB\nVmRSS:\t65536 kB\n"
        self.assertEqual(_parse_linux_vmrss_kib(valid), 65536)
        self.assertIsNone(_parse_linux_vmrss_kib("Name:\tpython\nVmHWM:\t9500 kB\n"))
        for invalid in ("VmRSS: -10 kB", "VmRSS: NaN kB", "VmRSS: 10 bytes",
                        "VmRSS: 184467440737095516160 kB", "VmRSS: 0 kB"):
            with self.subTest(invalid=invalid):
                self.assertIsNone(_parse_linux_vmrss_kib(invalid))

    def test_current_rss_returns_none_without_linux_procfs(self):
        from copticscriptorium_tf.converter import _current_rss_mb
        with patch("copticscriptorium_tf.converter.Path.read_text",
                   side_effect=FileNotFoundError):
            self.assertIsNone(_current_rss_mb())

    def test_phase_checkpoints_separate_current_and_highwater(self):
        from copticscriptorium_tf.converter import _memory_checkpoint
        with patch("copticscriptorium_tf.converter._current_rss_mb", return_value=33.5), patch(
            "copticscriptorium_tf.converter._peak_rss_mb", return_value=85.0,
        ):
            self.assertEqual(_memory_checkpoint(), {
                "current_rss_mb": 33.5,
                "peak_rss_mb": 85.0,
            })

    def test_real_native_converter_keeps_counts_and_records_all_checkpoints(self):
        from copticscriptorium_tf.converter import convert_source_tree
        with TemporaryDirectory() as tmp:
            source=Path(tmp)/"source"
            source.mkdir()
            _source_tree(source)
            result=convert_source_tree(
                source,Path(tmp)/"tf",
                upstream_repository="fixture/repo", upstream_commit=REVISION,
            )
            self.assertEqual((result.source_records,result.slots),(2,3))
            expected={
                "after_parse", "after_graph",
                "after_release_source", "after_write",
            }
            self.assertEqual(set(result.phase_memory_mb),expected)
            for checkpoint in result.phase_memory_mb.values():
                self.assertEqual(set(checkpoint),{"current_rss_mb","peak_rss_mb"})
                if checkpoint["current_rss_mb"] is not None:
                    self.assertGreater(checkpoint["current_rss_mb"],0)
                self.assertGreaterEqual(checkpoint["peak_rss_mb"],0)
            peaks=[result.phase_memory_mb[name]["peak_rss_mb"] for name in (
                "after_parse","after_graph","after_release_source","after_write",
            )]
            self.assertEqual(peaks,sorted(peaks))
            self.assertEqual(result.to_dict()["phase_memory_mb"],result.phase_memory_mb)
            self.assertTrue((Path(tmp)/"tf"/"otype.tf").is_file())

    def test_smoke_reloader_checkpoint_has_distinct_label(self):
        import importlib.util
        module_path=Path(__file__).resolve().parents[1]/"research"/"issue-16"/"full_converter_smoke.py"
        spec=importlib.util.spec_from_file_location("_issue16_memory_smoke",module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        run=module.run
        with TemporaryDirectory() as tmp:
            source=Path(tmp)/"source"
            source.mkdir()
            _source_tree(source)
            # The full-corpus smoke requires features (e.g. documented_overlap)
            # that this tiny fixture legitimately does not contain. Keep a
            # *real native TF reload* but limit the requested feature set to
            # source features this synthetic two-document graph can have.
            from tf.fabric import Fabric
            def limited_native_reload(tf_dir, conversion):
                api=Fabric(locations=[str(tf_dir)], silent="deep").load(
                    "source_record_id norm", silent="deep",
                )
                if not api:
                    raise AssertionError("minimal native TF reloader failed")
                if api.F.otype.maxSlot != conversion.slots:
                    raise AssertionError("native slot count differs")
                return {
                    "reload_slots": api.F.otype.maxSlot,
                    "structural_json_features": [
                        p.stem for p in tf_dir.glob("*_json.tf")
                    ],
                }
            with patch.object(module, "_reload_and_check", side_effect=limited_native_reload):
                result=run(source,Path(tmp)/"work")
            self.assertIn("after_parse",result["phase_memory_mb"])
            self.assertIn("after_write",result["phase_memory_mb"])
            self.assertIn("after_reload",result["phase_memory_mb"])
            self.assertEqual(result["reload_slots"],3)
            self.assertEqual(result["source_records"],2)
            self.assertEqual(result["structural_json_features"],[])
