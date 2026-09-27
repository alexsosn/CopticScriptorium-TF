"""RED-first summary-parent preflight regressions for issue #41."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


REVISION = "a" * 40


class SummaryParentPreflightTests(unittest.TestCase):
    def test_existing_file_ancestor_is_rejected_before_conversion(self):
        from copticscriptorium_tf.converter import _validate_summary_path, main

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            blocker = base / "not-a-directory"
            blocker.write_text("preserve me", encoding="utf-8")
            summary = blocker / "reports" / "summary.json"
            destination = base / "tf"

            with self.assertRaisesRegex(NotADirectoryError, "summary parent"):
                _validate_summary_path(summary, destination)

            with patch(
                "copticscriptorium_tf.converter.convert_source_tree",
                side_effect=AssertionError("conversion must not start"),
            ):
                code = main([
                    str(source), str(destination),
                    "--upstream-repository", "fixture/repo",
                    "--upstream-commit", REVISION,
                    "--summary", str(summary),
                ])

            self.assertNotEqual(code, 0)
            self.assertEqual(blocker.read_text(encoding="utf-8"), "preserve me")
            self.assertFalse(destination.exists())

    def test_dangling_symlink_ancestor_is_rejected_before_conversion(self):
        from copticscriptorium_tf.converter import _validate_summary_path, main

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            missing = base / "missing-parent"
            link = base / "dangling-parent"
            try:
                link.symlink_to(missing, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlinks unavailable: {error}")
            summary = link / "reports" / "summary.json"
            destination = base / "tf"

            with self.assertRaisesRegex(NotADirectoryError, "summary parent"):
                _validate_summary_path(summary, destination)

            with patch(
                "copticscriptorium_tf.converter.convert_source_tree",
                side_effect=AssertionError("conversion must not start"),
            ):
                code = main([
                    str(source), str(destination),
                    "--upstream-repository", "fixture/repo",
                    "--upstream-commit", REVISION,
                    "--summary", str(summary),
                ])

            self.assertNotEqual(code, 0)
            self.assertTrue(link.is_symlink())
            self.assertFalse(missing.exists())
            self.assertFalse(destination.exists())

    def test_symlink_to_directory_parent_remains_valid(self):
        from copticscriptorium_tf.converter import ConversionResult, main

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            actual_parent = base / "actual-reports"
            actual_parent.mkdir()
            linked_parent = base / "reports-link"
            try:
                linked_parent.symlink_to(actual_parent, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            destination = base / "tf"
            summary = linked_parent / "nested" / "summary.json"
            result = ConversionResult(
                source_records=0, slots=0, nodes=0, edges=0,
                output_path=destination, tf_files=0, tf_bytes=0,
                parse_seconds=0.0, graph_seconds=0.0, write_seconds=0.0,
                peak_rss_mb=0.0, missing_license_metadata_source_records=(),
            )

            with patch(
                "copticscriptorium_tf.converter.convert_source_tree",
                return_value=result,
            ):
                code = main([
                    str(source), str(destination),
                    "--upstream-repository", "fixture/repo",
                    "--upstream-commit", REVISION,
                    "--summary", str(summary),
                ])

            self.assertEqual(code, 0)
            self.assertTrue(linked_parent.is_symlink())
            self.assertTrue((actual_parent / "nested" / "summary.json").is_file())

    def test_missing_nested_parent_under_directory_remains_valid(self):
        from copticscriptorium_tf.converter import ConversionResult, main

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            destination = base / "tf"
            summary = base / "reports" / "nested" / "summary.json"
            result = ConversionResult(
                source_records=0, slots=0, nodes=0, edges=0,
                output_path=destination, tf_files=0, tf_bytes=0,
                parse_seconds=0.0, graph_seconds=0.0, write_seconds=0.0,
                peak_rss_mb=0.0, missing_license_metadata_source_records=(),
            )

            with patch(
                "copticscriptorium_tf.converter.convert_source_tree",
                return_value=result,
            ):
                code = main([
                    str(source), str(destination),
                    "--upstream-repository", "fixture/repo",
                    "--upstream-commit", REVISION,
                    "--summary", str(summary),
                ])

            self.assertEqual(code, 0)
            self.assertTrue(summary.is_file())


if __name__ == "__main__":
    unittest.main()
