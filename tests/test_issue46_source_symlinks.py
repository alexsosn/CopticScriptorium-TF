"""RED-first source-boundary regressions for issue #46."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from copticscriptorium_tf.parser import parse_source_tree


TT = b'<meta corpus="fixture"/><norm_group norm_group="a"><norm xml:id="w1" norm="a" new_sent="true">a</norm></norm_group>'


class SourceSymlinkBoundaryTests(unittest.TestCase):
    def _root(self, base: Path) -> Path:
        root = base / "source"
        (root / "alpha" / "alpha_TT").mkdir(parents=True)
        return root

    def _parse(self, root: Path):
        return parse_source_tree(
            root,
            upstream_repository="fixture/repo",
            upstream_commit="unversioned-local",
        )

    def test_live_tt_symlink_is_rejected_instead_of_reading_external_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = self._root(base)
            outside = base / "outside.tt"
            outside.write_bytes(TT)
            link = root / "alpha" / "alpha_TT" / "escape.tt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with self.assertRaisesRegex(ValueError, "symlinked TT source record"):
                self._parse(root)

    def test_dangling_tt_symlink_is_rejected_instead_of_silently_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = self._root(base)
            link = root / "alpha" / "alpha_TT" / "missing.tt"
            try:
                link.symlink_to(base / "does-not-exist.tt")
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with self.assertRaisesRegex(ValueError, "symlinked TT source record"):
                self._parse(root)

    def test_physical_tt_file_remains_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(Path(tmp))
            (root / "alpha" / "alpha_TT" / "physical.tt").write_bytes(TT)
            documents = self._parse(root)
            self.assertEqual([d.source_record_id for d in documents], ["alpha/alpha:physical"])


if __name__ == "__main__":
    unittest.main()
