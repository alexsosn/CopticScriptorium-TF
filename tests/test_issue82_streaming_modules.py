"""RED-first streaming bilateral native Coptic↔LXX weft modules (#82).

Small tests compare the existing implementation against a one-pass unordered
source iterator; full-source complexity and resource bounds require live CI.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric

from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph
from copticscriptorium_tf.lxx_module import (
    COPTIC_PIN, LXX_PIN,
    materialize_lxx_reference_modules,
    materialize_lxx_reference_modules_streaming,
    verify_coptic_module_parent,
)
from tests.test_issue73_lxx_dual_tf_modules import source, _FakeLxxApi


class StreamingNativeReferenceModulesTests(unittest.TestCase):
    def _parents(self, root: Path):
        first = source("sahidic.ruth/d1:Ruth_02", "ⲁ")
        second = source("sahidic.ruth/d2:Ruth_02", "ⲃ")
        parent = root / "coptic-tf"
        write_graph(build_graph([first, second]), parent)
        api = Fabric(locations=[str(parent)], silent="deep").load(
            "source_record_id source_word_ordinal", silent="deep"
        )
        self.assertTrue(api)
        return (first, second), parent, api

    def _kwargs(self, parent: Path, api):
        return dict(
            coptic_api=api,
            lxx_api=_FakeLxxApi(),
            lxx_parent_commit=LXX_PIN,
            coptic_source_commit=COPTIC_PIN,
            coptic_parent_tf=parent,
            verify_parent_feature_hashes=False,
        )

    def test_one_pass_unordered_documents_match_legacy_native_tf_bytes(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            documents, parent, api = self._parents(root)
            expected = root / "legacy"
            old = materialize_lxx_reference_modules(
                documents=documents, output_root=expected,
                **self._kwargs(parent, api)
            )
            seen = []
            def one_pass():
                for doc in reversed(documents):
                    seen.append(doc.source_record_id)
                    yield doc
            actual = root / "streamed"
            got = materialize_lxx_reference_modules_streaming(
                documents=one_pass(), output_root=actual,
                **self._kwargs(parent, api)
            )
            self.assertEqual(got, old)
            self.assertEqual(len(seen), 2)
            for side in ("coptic", "lxx"):
                names = sorted(p.name for p in (expected / side).glob("*.tf"))
                self.assertEqual(names, sorted(p.name for p in (actual / side).glob("*.tf")))
                for name in names:
                    self.assertEqual(
                        (expected / side / name).read_bytes(),
                        (actual / side / name).read_bytes(),
                        (side, name),
                    )
            verify_coptic_module_parent(actual / "coptic", parent)
            overlay = Fabric(
                locations=[str(parent), str(actual / "coptic")], silent="deep"
            ).load("coptic_lxx_ref_id coptic_lxx_ref_status", silent="deep")
            self.assertTrue(overlay)
            self.assertEqual(overlay.F.otype.maxSlot, 2)
            self.assertEqual(
                [overlay.F.coptic_lxx_ref_id.v(i) for i in (1, 2)],
                ["CenterBLC/LXX:1935:Ruth:2:1"] * 2,
            )

    def test_git_blob_hash_stream_matches_real_sha1_object_header(self):
        """Regression for NUL vs literal backslash-zero in streamed Git blobs."""
        from hashlib import sha1
        from unittest.mock import patch
        from copticscriptorium_tf import lxx_module
        payload = b"TF-TEST\0" * 160_000  # cross a 1 MiB read boundary
        expected = sha1(
            b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        ).hexdigest()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "sentinel.tf"
            source.write_bytes(payload)
            with patch.dict(
                lxx_module.LXX_FEATURE_GIT_BLOBS, {"sentinel": expected}, clear=True
            ):
                lxx_module.verify_lxx_parent_feature_blobs(root)
                source.write_bytes(payload[:-1] + b"X")
                with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                    lxx_module.verify_lxx_parent_feature_blobs(root)

    def test_missing_or_extra_source_document_fails_atomically(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            docs, parent, api = self._parents(root)
            for label, selected in (("missing", docs[:1]), ("extra", (*docs, docs[0]))):
                target = root / label
                with self.subTest(label=label):
                    with self.assertRaisesRegex(ValueError, "duplicate|missing|incomplete|source"):
                        materialize_lxx_reference_modules_streaming(
                            documents=iter(selected), output_root=target,
                            **self._kwargs(parent, api)
                        )
                    self.assertFalse(target.exists())

    def test_casefold_colliding_source_records_fail_atomically(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            docs, parent, api = self._parents(root)
            # Alternative spelling of the same source identity is not a new
            # witness; detect ambiguity before attaching it to a TF parent.
            from dataclasses import replace
            collision = replace(docs[0], source_record_id=docs[0].source_record_id.upper())
            target = root / "collision"
            with self.assertRaisesRegex(ValueError, "duplicate|casefold"):
                materialize_lxx_reference_modules_streaming(
                    documents=iter((docs[0], collision)), output_root=target,
                    **self._kwargs(parent, api)
                )
            self.assertFalse(target.exists())

    def test_changed_generated_parent_fingerprint_rejects_overlay(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            docs, parent, api = self._parents(root)
            target = root / "streamed"
            materialize_lxx_reference_modules_streaming(
                documents=iter(docs), output_root=target,
                **self._kwargs(parent, api)
            )
            with (parent / "source_word_ordinal.tf").open("a", encoding="utf8") as out:
                out.write("\n")
            with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
                verify_coptic_module_parent(target / "coptic", parent)


if __name__ == "__main__":
    unittest.main()
