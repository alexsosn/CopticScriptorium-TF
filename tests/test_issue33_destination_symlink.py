"""RED-first destination path regression for issue #33."""
from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.writer import write_graph


TT = (
    '<meta corpus="alpha" document_cts_urn="urn:cts:copticLit:fixture.a">'
    '<norm_group norm_group="a"><norm xml:id="u1" new_sent="true" '
    'func="root" pos="N" lemma="a" norm="a">a</norm></norm_group>'
)


@unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
class DanglingDestinationTests(unittest.TestCase):
    def _dangling_link(self, root: Path) -> tuple[Path, str]:
        target = root / "missing-target"
        link = root / "output-tf"
        link.symlink_to(target)
        self.assertTrue(link.is_symlink())
        self.assertFalse(link.exists())
        return link, os.readlink(link)

    def test_converter_rejects_dangling_destination_before_parsing(self) -> None:
        from copticscriptorium_tf.converter import convert_source_tree

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            link, literal_target = self._dangling_link(root)

            with patch(
                "copticscriptorium_tf.converter.parse_source_tree",
                side_effect=AssertionError("source parsing must not start"),
            ) as parse:
                with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                    convert_source_tree(
                        root / "source-does-not-need-to-exist",
                        link,
                        upstream_repository="fixture/repo",
                        upstream_commit="a" * 40,
                    )

            parse.assert_not_called()
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), literal_target)
            self.assertFalse(link.exists())

    def test_writer_rejects_dangling_destination_without_replacing_link(self) -> None:
        document = parse_tt_record(
            TT.encode("utf-8"),
            source_record_id="alpha/alpha:a",
            source_path="alpha/alpha_TT/a.tt",
            upstream_repository="fixture/repo",
            upstream_commit="a" * 40,
        )
        graph = build_graph([document])

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            link, literal_target = self._dangling_link(root)

            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                write_graph(graph, link)

            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), literal_target)
            self.assertFalse(link.exists())


if __name__ == "__main__":
    unittest.main()
