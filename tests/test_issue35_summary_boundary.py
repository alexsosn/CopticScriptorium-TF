"""RED-first artifact-boundary regressions for issue #35."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


class SummaryBoundaryTests(unittest.TestCase):
    def test_direct_cli_rejects_summary_inside_tf_destination_before_conversion(self):
        from copticscriptorium_tf.converter import main

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            for summary in (
                base / "tf",
                base / "tf" / "conversion-summary.json",
                base / "tf" / "reports" / "conversion-summary.json",
            ):
                destination = base / "tf"
                with self.subTest(summary=summary):
                    with patch(
                        "copticscriptorium_tf.converter.convert_source_tree",
                        side_effect=AssertionError("conversion must not start"),
                    ):
                        code = main([
                            str(source),
                            str(destination),
                            "--upstream-repository", "fixture/repo",
                            "--upstream-commit", "deadbeef",
                            "--summary", str(summary),
                        ])
                    self.assertNotEqual(code, 0)
                    self.assertFalse(destination.exists())

    def test_direct_cli_allows_summary_outside_tf_destination(self):
        from copticscriptorium_tf.converter import ConversionResult, main

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            destination = base / "tf"
            summary = base / "conversion-summary.json"
            result = ConversionResult(
                source_records=0, slots=0, nodes=0, edges=0,
                output_path=destination, tf_files=0, tf_bytes=0,
                parse_seconds=0.0, graph_seconds=0.0, write_seconds=0.0,
                peak_rss_mb=0.0, missing_license_metadata_source_records=(),
            )
            with patch("copticscriptorium_tf.converter.convert_source_tree", return_value=result):
                self.assertEqual(main([
                    str(source),
                    str(destination),
                    "--upstream-repository", "fixture/repo",
                    "--upstream-commit", "deadbeef",
                    "--summary", str(summary),
                ]), 0)
            self.assertTrue(summary.is_file())


if __name__ == "__main__":
    unittest.main()
