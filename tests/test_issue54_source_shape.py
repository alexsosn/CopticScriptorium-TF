"""RED-first supported source path type regressions for issue #54."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from copticscriptorium_tf.parser import parse_source_tree


TT = (
    '<meta corpus="alpha" document_cts_urn="urn:cts:copticLit:fixture.a">'
    '<norm_group norm_group="a"><norm xml:id="w1" norm="a" new_sent="true" '
    'func="root" pos="N" lemma="a">a</norm></norm_group>'
).encode("utf-8")


class SupportedSourcePathTypeTests(unittest.TestCase):
    def _parse(self, root: Path):
        return parse_source_tree(
            root,
            upstream_repository="fixture/repo",
            upstream_commit="unversioned-local",
        )

    def _valid_dataset(self, root: Path, name: str = "good") -> Path:
        directory = root / "alpha" / f"{name}_TT"
        directory.mkdir(parents=True)
        (directory / "doc.tt").write_bytes(TT)
        return directory

    def test_dataset_candidate_must_be_a_directory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            self._valid_dataset(root)
            malformed = root / "alpha" / "bad_TT"
            malformed.write_text("not a dataset directory", encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                "TT dataset candidate must be a directory",
            ):
                self._parse(root)

    def test_tt_record_candidate_must_be_a_regular_file(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            dataset = self._valid_dataset(root)
            (dataset / "bad.tt").mkdir()

            with self.assertRaisesRegex(
                ValueError,
                "TT source record candidate must be a regular file",
            ):
                self._parse(root)

    def test_archive_candidate_must_be_a_regular_file_before_zip_open(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            self._valid_dataset(root)
            (root / "alpha" / "bad_TT.zip").mkdir()

            with self.assertRaisesRegex(
                ValueError,
                "TT archive package must be a regular file",
            ):
                self._parse(root)

    def test_unrelated_non_tt_paths_remain_ignored(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            self._valid_dataset(root)
            (root / "alpha" / "notes.txt").write_text("notes", encoding="utf-8")
            (root / "alpha" / "misc").mkdir()
            (root / "alpha" / "misc" / "nested.bin").write_bytes(b"x")

            documents = self._parse(root)

            self.assertEqual([document.source_record_id for document in documents], ["alpha/good:doc"])


if __name__ == "__main__":
    unittest.main()
