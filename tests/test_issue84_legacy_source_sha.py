"""RED-first legacy Coptic↔LXX source-byte identity contracts (#84)."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph
from copticscriptorium_tf.lxx_module import (
    COPTIC_PIN, LXX_PIN, materialize_lxx_reference_modules,
)
from tests.test_issue73_lxx_dual_tf_modules import source, _FakeLxxApi


class LegacyCopticLxxSourceIdentityTests(unittest.TestCase):
    def _fixture(self, root: Path, *, load_hash: bool = True):
        model = source("sahidic.ruth/d1:Ruth_02", "ⲁ")
        parent = root / "parent"
        write_graph(build_graph([model]), parent)
        features = "source_record_id source_word_ordinal"
        if load_hash:
            features += " source_sha256"
        api = Fabric(locations=[str(parent)], silent="deep").load(
            features, silent="deep"
        )
        assert api
        return model, parent, api

    def _run(self, root: Path, model, parent: Path, api):
        return materialize_lxx_reference_modules(
            documents=(model,),
            coptic_api=api,
            lxx_api=_FakeLxxApi(),
            output_root=root / "module",
            lxx_parent_commit=LXX_PIN,
            coptic_source_commit=COPTIC_PIN,
            coptic_parent_tf=parent,
            verify_parent_feature_hashes=False,
        )

    def test_red_legacy_rejects_drifted_source_sha_without_publishing(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            model, parent, api = self._fixture(root)
            drift = replace(model, source_sha256="f" * 64)
            with self.assertRaisesRegex(ValueError, "source SHA-256 mismatch"):
                self._run(root, drift, parent, api)
            self.assertFalse((root / "module").exists())

    def test_red_legacy_rejects_parent_api_without_loaded_source_sha(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            model, parent, api = self._fixture(root, load_hash=False)
            with self.assertRaisesRegex(ValueError, "source_sha256"):
                self._run(root, model, parent, api)
            self.assertFalse((root / "module").exists())

    def test_valid_unchanged_pilot_remains_native_tf_loadable(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            model, parent, api = self._fixture(root)
            result = self._run(root, model, parent, api)
            self.assertEqual(result.source_documents, 1)
            weft = root / "module" / "coptic"
            combined = Fabric(locations=[str(parent), str(weft)], silent="deep").load(
                "coptic_lxx_ref_id coptic_lxx_ref_status", silent="deep"
            )
            self.assertTrue(combined)
            self.assertEqual(combined.F.coptic_lxx_ref_status.v(1), "reference_candidate")


if __name__ == "__main__":
    unittest.main()
