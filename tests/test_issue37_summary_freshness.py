"""RED-first fresh-summary-path regressions for issue #37."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


def _cli_args(source: Path, destination: Path, summary: Path) -> list[str]:
    return [
        str(source),
        str(destination),
        "--upstream-repository", "fixture/repo",
        "--upstream-commit", "deadbeef",
        "--summary", str(summary),
    ]


class SummaryFreshPathTests(unittest.TestCase):
    def test_existing_file_and_directory_are_rejected_before_conversion(self):
        from copticscriptorium_tf.converter import main

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            existing_file = base / "existing-summary.json"
            existing_file.write_text("keep me", encoding="utf-8")
            existing_dir = base / "existing-summary-dir"
            existing_dir.mkdir()

            for summary in (existing_file, existing_dir):
                destination = base / f"tf-{summary.name}"
                with self.subTest(summary=summary):
                    with patch(
                        "copticscriptorium_tf.converter.convert_source_tree",
                        side_effect=AssertionError("conversion must not start"),
                    ):
                        code = main(_cli_args(source, destination, summary))
                    self.assertNotEqual(code, 0)
                    self.assertFalse(destination.exists())

            self.assertEqual(existing_file.read_text(encoding="utf-8"), "keep me")
            self.assertEqual(list(existing_dir.iterdir()), [])

    def test_existing_symlink_is_rejected_without_touching_its_target(self):
        from copticscriptorium_tf.converter import main

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            target = base / "important.txt"
            target.write_text("preserve target", encoding="utf-8")
            summary = base / "summary-link.json"
            try:
                summary.symlink_to(target)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            destination = base / "tf"
            with patch(
                "copticscriptorium_tf.converter.convert_source_tree",
                side_effect=AssertionError("conversion must not start"),
            ):
                code = main(_cli_args(source, destination, summary))

            self.assertNotEqual(code, 0)
            self.assertTrue(summary.is_symlink())
            self.assertEqual(target.read_text(encoding="utf-8"), "preserve target")
            self.assertFalse(destination.exists())

    def test_dangling_symlink_is_also_an_occupied_summary_path(self):
        from copticscriptorium_tf.converter import main

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            missing_target = base / "missing-target.json"
            summary = base / "dangling-summary.json"
            try:
                summary.symlink_to(missing_target)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            destination = base / "tf"
            with patch(
                "copticscriptorium_tf.converter.convert_source_tree",
                side_effect=AssertionError("conversion must not start"),
            ):
                code = main(_cli_args(source, destination, summary))

            self.assertNotEqual(code, 0)
            self.assertTrue(summary.is_symlink())
            self.assertFalse(missing_target.exists())
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
