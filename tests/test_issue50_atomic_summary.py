"""RED-first atomic direct-summary regressions for issue #50."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from copticscriptorium_tf import converter


def _result(output: Path) -> converter.ConversionResult:
    return converter.ConversionResult(
        source_records=2,
        slots=3,
        nodes=4,
        edges=5,
        output_path=output,
        tf_files=6,
        tf_bytes=7,
        parse_seconds=1.25,
        graph_seconds=2.5,
        write_seconds=3.75,
        peak_rss_mb=42.0,
        missing_license_metadata_source_records=("alpha/a:one",),
    )


class AtomicSummaryTests(unittest.TestCase):
    def test_staged_write_failure_never_creates_final_summary_and_cleans_temp(self):
        stager = getattr(converter, "_stage_summary_payload", None)
        self.assertIsNotNone(
            stager,
            "converter must stage summary bytes before final publication",
        )

        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            summary = parent / "conversion-summary.json"
            staged = parent / ".conversion-summary.json.test.tmp"

            class FailingTemporaryFile:
                name = str(staged)

                def __enter__(self):
                    staged.write_text("partial", encoding="utf-8")
                    return self

                def write(self, _payload):
                    raise OSError("simulated summary write failure")

                def __exit__(self, exc_type, exc, tb):
                    return False

            with patch.object(
                converter,
                "NamedTemporaryFile",
                return_value=FailingTemporaryFile(),
            ):
                with self.assertRaisesRegex(OSError, "simulated summary write failure"):
                    stager(summary, '{"complete": true}\n')

            self.assertFalse(summary.exists())
            self.assertFalse(staged.exists())
            self.assertEqual(list(parent.glob(".conversion-summary.json.*.tmp")), [])

    def test_publish_race_preserves_competing_file_directory_and_symlink(self):
        publisher = getattr(converter, "_publish_summary_no_clobber", None)

        for kind in ("file", "directory", "symlink"):
            with self.subTest(kind=kind), TemporaryDirectory() as temporary:
                parent = Path(temporary)
                summary = parent / "conversion-summary.json"
                output = parent / "tf"
                target = parent / "important-target"
                target.write_text("target", encoding="utf-8")

                def competing_publish(staged: Path, final: Path):
                    if kind == "file":
                        final.write_text("competitor", encoding="utf-8")
                    elif kind == "directory":
                        final.mkdir()
                    else:
                        try:
                            final.symlink_to(target)
                        except (OSError, NotImplementedError) as error:
                            self.skipTest(f"symlinks unavailable: {error}")
                    if publisher is None:
                        raise AssertionError("atomic summary publisher missing")
                    return publisher(staged, final)

                with patch.object(
                    converter,
                    "_publish_summary_no_clobber",
                    side_effect=competing_publish,
                    create=True,
                ):
                    with self.assertRaises(FileExistsError):
                        converter._write_summary(summary, _result(output))

                if kind == "file":
                    self.assertEqual(summary.read_text(encoding="utf-8"), "competitor")
                elif kind == "directory":
                    self.assertTrue(summary.is_dir())
                    self.assertEqual(tuple(summary.iterdir()), ())
                else:
                    self.assertTrue(summary.is_symlink())
                    self.assertEqual(summary.resolve(), target.resolve())
                    self.assertEqual(target.read_text(encoding="utf-8"), "target")
                self.assertEqual(list(parent.glob(".conversion-summary.json.*.tmp")), [])

    def test_successful_summary_preserves_existing_schema_and_json_bytes_contract(self):
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            summary = parent / "conversion-summary.json"
            result = _result(parent / "tf")

            converter._write_summary(summary, result)

            self.assertEqual(json.loads(summary.read_text(encoding="utf-8")), result.to_dict())
            self.assertTrue(summary.read_bytes().endswith(b"\n"))
            self.assertEqual(list(parent.glob(".conversion-summary.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
