"""RED-first non-empty dataset regressions for issue #56."""
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


class NonEmptyDatasetTests(unittest.TestCase):
    def _parse(self, root: Path):
        return parse_source_tree(
            root,
            upstream_repository="fixture/repo",
            upstream_commit="unversioned-local",
        )

    def _valid_directory(self, root: Path, dataset: str = "good") -> None:
        directory = root / "alpha" / f"{dataset}_TT"
        directory.mkdir(parents=True)
        (directory / "doc.tt").write_bytes(TT)

    def test_empty_physical_tt_dataset_fails_instead_of_disappearing(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            self._valid_directory(root)
            empty = root / "alpha" / "empty_TT"
            empty.mkdir()
            (empty / "README.txt").write_text("not a TT record", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "TT dataset contains no supported TT records"):
                self._parse(root)

    def test_empty_physical_tt_archive_fails_instead_of_disappearing(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            self._valid_directory(root)
            archive_path = root / "alpha" / "empty_TT.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("empty_TT/README.txt", b"not a TT record")

            with self.assertRaisesRegex(ValueError, "TT archive contains no supported TT records"):
                self._parse(root)

    def test_non_tt_files_are_allowed_when_directory_has_a_valid_tt_record(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            directory = root / "alpha" / "good_TT"
            directory.mkdir(parents=True)
            (directory / "doc.tt").write_bytes(TT)
            (directory / "README.txt").write_text("notes", encoding="utf-8")

            documents = self._parse(root)
            self.assertEqual([d.source_record_id for d in documents], ["alpha/good:doc"])

    def test_non_tt_members_are_allowed_when_archive_has_a_valid_tt_record(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            corpus = root / "alpha"
            corpus.mkdir(parents=True)
            archive_path = corpus / "good_TT.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("good_TT/doc.tt", TT)
                archive.writestr("good_TT/README.txt", b"notes")

            documents = self._parse(root)
            self.assertEqual([d.source_record_id for d in documents], ["alpha/good:doc"])
            self.assertEqual(documents[0].packaging, "archive")


if __name__ == "__main__":
    unittest.main()
