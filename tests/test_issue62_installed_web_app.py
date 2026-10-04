"""RED-first installed Text-Fabric web-app launcher contract for issue #62."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from copticscriptorium_tf import web_app


ROOT = Path(__file__).resolve().parents[1]


class InstalledWebAppLauncherTests(unittest.TestCase):
    def _tf_dir(self, root: Path) -> Path:
        tf_dir = root / "generated-tf"
        tf_dir.mkdir()
        for name in ("otype.tf", "oslots.tf", "otext.tf"):
            (tf_dir / name).write_text("@node\n", encoding="utf-8")
        return tf_dir

    def test_source_checkout_finds_the_canonical_app_config(self):
        with web_app.app_directory() as app_dir:
            self.assertEqual(
                (app_dir / "config.yaml").read_bytes(),
                (ROOT / "app" / "config.yaml").read_bytes(),
            )

    def test_browser_arguments_use_packaged_app_and_generated_tf_location(self):
        app_dir = Path("/fixture/app")
        tf_dir = Path("/fixture/generated tf")
        self.assertEqual(
            web_app.browser_arguments(
                app_dir,
                tf_dir,
                ("-noweb", "--tool=ner"),
            ),
            (
                "app:/fixture/app",
                "--locations=/fixture/generated tf",
                "--modules=.",
                "-noweb",
                "--tool=ner",
            ),
        )

    def test_check_mode_constructs_standard_browser_without_starting_server(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            tf_dir = self._tf_dir(root)
            expected_app = ROOT / "app"
            sentinel = object()
            with (
                patch.object(web_app, "app_directory") as app_directory,
                patch.object(
                    web_app,
                    "setup_browser",
                    return_value=sentinel,
                ) as setup_browser,
                patch.object(web_app, "start_browser") as start_browser,
            ):
                app_directory.return_value.__enter__.return_value = expected_app
                app_directory.return_value.__exit__.return_value = False
                status = web_app.main([str(tf_dir), "--check"])

            self.assertEqual(status, 0)
            setup_browser.assert_called_once_with(
                False,
                f"app:{expected_app}",
                f"--locations={tf_dir.resolve()}",
                "--modules=.",
            )
            start_browser.assert_not_called()

    def test_normal_mode_delegates_to_text_fabric_browser_start(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            tf_dir = self._tf_dir(root)
            expected_app = ROOT / "app"
            with (
                patch.object(web_app, "app_directory") as app_directory,
                patch.object(web_app, "setup_browser") as setup_browser,
                patch.object(web_app, "start_browser") as start_browser,
            ):
                app_directory.return_value.__enter__.return_value = expected_app
                app_directory.return_value.__exit__.return_value = False
                status = web_app.main(
                    [str(tf_dir), "-noweb", "--tool=ner"]
                )

            self.assertEqual(status, 0)
            start_browser.assert_called_once_with(
                (
                    f"app:{expected_app}",
                    f"--locations={tf_dir.resolve()}",
                    "--modules=.",
                    "-noweb",
                    "--tool=ner",
                )
            )
            setup_browser.assert_not_called()

    def test_missing_generated_tf_fails_before_text_fabric_start(self):
        with TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing"
            with (
                patch.object(web_app, "setup_browser") as setup_browser,
                patch.object(web_app, "start_browser") as start_browser,
            ):
                status = web_app.main([str(missing), "--check"])
            self.assertEqual(status, 1)
            setup_browser.assert_not_called()
            start_browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()
