"""RED-first archive source-boundary regressions for issue #52."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from copticscriptorium_tf.parser import parse_source_tree


TT = (
    '<meta corpus="alpha" document_cts_urn="urn:cts:copticLit:fixture.a">'
    '<norm_group norm_group="a"><norm xml:id="w1" norm="a" new_sent="true" '
    'func="root" pos="N" lemma="a">a</norm></norm_group>'
).encode("utf-8")


class ZipSymlinkBoundaryTests(unittest.TestCase):
    def _root(self, base: Path) -> Path:
        root = base / "source"
        (root / "alpha").mkdir(parents=True)
        return root

    def _archive(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("alpha_TT/doc.tt", TT)

    def _parse(self, root: Path):
        return parse_source_tree(
            root,
            upstream_repository="fixture/repo",
            upstream_commit="unversioned-local",
        )

    def test_live_zip_symlink_is_rejected_before_external_archive_is_opened(self):
        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self._root(base)
            outside = base / "outside" / "alpha_TT.zip"
            self._archive(outside)
            link = root / "alpha" / "alpha_TT.zip"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with self.assertRaisesRegex(ValueError, "symlinked TT archive package"):
                self._parse(root)

    def test_dangling_zip_symlink_is_rejected_deterministically(self):
        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self._root(base)
            link = root / "alpha" / "alpha_TT.zip"
            try:
                link.symlink_to(base / "missing" / "alpha_TT.zip")
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with self.assertRaisesRegex(ValueError, "symlinked TT archive package"):
                self._parse(root)

    def test_physical_zip_package_retains_existing_semantics(self):
        with TemporaryDirectory() as temporary:
            root = self._root(Path(temporary))
            archive = root / "alpha" / "alpha_TT.zip"
            self._archive(archive)

            documents = self._parse(root)

            self.assertEqual(len(documents), 1)
            document = documents[0]
            self.assertEqual(document.source_record_id, "alpha/alpha:doc")
            self.assertEqual(document.packaging, "archive")
            self.assertEqual(
                document.source_path,
                "alpha/alpha_TT.zip!/alpha_TT/doc.tt",
            )


if __name__ == "__main__":
    unittest.main()
