"""RED-first immutable provenance regressions for issue #39."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


class ImmutableProvenanceTests(unittest.TestCase):
    def test_symbolic_and_abbreviated_revisions_fail_before_source_parsing(self):
        from copticscriptorium_tf.converter import convert_source_tree

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            for revision in ("main", "deadbeef", "v1.0.0", "", "g" * 40):
                with self.subTest(revision=revision):
                    with patch(
                        "copticscriptorium_tf.converter.parse_source_tree",
                        side_effect=AssertionError("source parsing must not start"),
                    ):
                        with self.assertRaisesRegex(ValueError, "upstream commit"):
                            convert_source_tree(
                                base / "source",
                                base / f"tf-{len(revision)}-{revision[:4]}",
                                upstream_repository="fixture/repo",
                                upstream_commit=revision,
                            )

    def test_full_git_hashes_and_explicit_unversioned_local_pass_provenance_gate(self):
        from copticscriptorium_tf.converter import convert_source_tree

        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            for revision in ("a" * 40, "b" * 64, "unversioned-local"):
                with self.subTest(revision=revision):
                    with patch(
                        "copticscriptorium_tf.converter.parse_source_tree",
                        return_value=[],
                    ) as parse:
                        with self.assertRaisesRegex(ValueError, "no supported TT source records"):
                            convert_source_tree(
                                base / "source",
                                base / f"tf-{len(revision)}",
                                upstream_repository="fixture/repo",
                                upstream_commit=revision,
                            )
                    parse.assert_called_once()


if __name__ == "__main__":
    unittest.main()
