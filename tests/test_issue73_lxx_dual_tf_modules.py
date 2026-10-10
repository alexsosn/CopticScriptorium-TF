"""RED-first native bilateral Text-Fabric mapping module contract, issue #73."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph
from copticscriptorium_tf.lxx_module import (
    materialize_lxx_reference_modules,
    verify_lxx_parent_feature_blobs,
)
from tf.fabric import Fabric

COPTIC_SOURCE_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
LXX_PARENT_COMMIT = "f32a98eddf7eb239aa73ab863d70381e416d5076"


def source(path: str, label: str, book: str = "Ruth"):
    raw = (
        f'<meta book="{book}" chapter="2">'
        '<verse_n verse_n="1">'
        f'<norm_group norm_group="{label}">'
        f'<norm xml:id="u1" new_sent="true" func="root" norm="{label}">'
        f'{label}</norm></norm_group>'
    )
    corpus = path.split("/", 1)[0]
    return parse_tt_record(
        raw.encode("utf-8"),
        source_record_id=path, source_path=path,
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=COPTIC_SOURCE_COMMIT,
    )


class _FakeLxxApi:
    def __init__(self):
        self.F = SimpleNamespace(otype=SimpleNamespace(
            maxSlot=623693, maxNode=685732,
            s=lambda kind: tuple(range(655362, 685733)) if kind == "verse" else (),
            v=lambda n: "verse" if n == 663156 else "word",
        ))
        self.T = SimpleNamespace(nodeFromSection=lambda ref: 663156 if ref == ("Ruth", 2, 1) else None)


class LxxBilateralModuleTests(unittest.TestCase):
    def test_project_two_coptic_witnesses_to_one_lxx_verse_without_cross_warp_links(self):
        first = source("sahidic.ruth/d1:Ruth_02", "ⲁ")
        second = source("sahidic.ruth/d2:Ruth_02", "ⲃ")
        with TemporaryDirectory() as root:
            root = Path(root)
            coptic_path = root / "parent"
            write_graph(build_graph([first, second]), coptic_path)
            coptic_api = Fabric(locations=[str(coptic_path)], silent="deep").load(
                "source_record_id source_word_ordinal", silent="deep"
            )
            modules = root / "modules"
            summary = materialize_lxx_reference_modules(
                documents=(first, second),
                coptic_api=coptic_api,
                lxx_api=_FakeLxxApi(),
                output_root=modules,
                lxx_parent_commit=LXX_PARENT_COMMIT,
                coptic_source_commit=COPTIC_SOURCE_COMMIT,
                coptic_parent_tf=coptic_path,
                verify_parent_feature_hashes=False,
            )
            self.assertEqual(summary.coptic_candidate_words, 2)
            self.assertEqual(summary.lxx_candidate_verses, 1)
            coptic_module = modules / "coptic"
            greek_module = modules / "lxx"
            for path in (coptic_module, greek_module):
                self.assertTrue((path / "coptic_lxx_ref_id.tf").exists())
                self.assertFalse((path / "otype.tf").exists())
                self.assertFalse((path / "oslots.tf").exists())
                self.assertFalse((path / "otext.tf").exists())
            api = Fabric(locations=[str(coptic_path), str(coptic_module)], silent="deep").load(
                "source_record_id coptic_lxx_ref_id coptic_lxx_ref_status", silent="deep"
            )
            self.assertEqual(api.F.otype.maxSlot, 2)
            self.assertEqual(api.F.coptic_lxx_ref_id.v(1), "CenterBLC/LXX:1935:Ruth:2:1")
            self.assertEqual(api.F.coptic_lxx_ref_id.v(2), "CenterBLC/LXX:1935:Ruth:2:1")
            self.assertEqual(api.F.coptic_lxx_ref_status.v(1), "reference_candidate")
            self.assertEqual(api.F.coptic_lxx_ref_status.v(2), "reference_candidate")
            greek_text = (greek_module / "coptic_lxx_ref_id.tf").read_text()
            self.assertIn("663156\tCenterBLC/LXX:1935:Ruth:2:1", greek_text)
            self.assertNotIn("source_record_id", greek_text)
            self.assertIn("@parentCommit="+LXX_PARENT_COMMIT, greek_text)
            coptic_text = (coptic_module / "coptic_lxx_ref_id.tf").read_text()
            self.assertIn("@parentRepo=CopticScriptorium-TF/generated", coptic_text)
            self.assertIn("@parentFingerprintSha256=", coptic_text)
            self.assertIn("@copticSourceCommit="+COPTIC_SOURCE_COMMIT, coptic_text)
            self.assertNotIn("@parentCommit="+COPTIC_SOURCE_COMMIT, coptic_text)


    def test_rejects_wrong_greek_release_even_if_node_counts_appear_valid(self):
        first = source("sahidic.ruth/d1:Ruth_02", "ⲁ")
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "pinned LXX parent"):
                materialize_lxx_reference_modules(
                    documents=(first,),
                    coptic_api=None,
                    lxx_api=_FakeLxxApi(),
                    output_root=Path(temp) / "modules",
                    lxx_parent_commit="0"*40,
                    coptic_source_commit=COPTIC_SOURCE_COMMIT,
                    verify_parent_feature_hashes=False,
                )

    def test_missing_generated_coptic_parent_cannot_be_claimed_by_module(self):
        first = source("sahidic.ruth/d1:Ruth_02", "ⲁ")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            coptic_path = root / "parent"
            write_graph(build_graph([first]), coptic_path)
            coptic_api = Fabric(locations=[str(coptic_path)], silent="deep").load(
                "source_record_id source_word_ordinal", silent="deep"
            )
            with self.assertRaisesRegex(ValueError, "missing.*Coptic parent"):
                materialize_lxx_reference_modules(
                    documents=(first,),
                    coptic_api=coptic_api,
                    lxx_api=_FakeLxxApi(),
                    output_root=root / "modules",
                    lxx_parent_commit=LXX_PARENT_COMMIT,
                    coptic_source_commit=COPTIC_SOURCE_COMMIT,
                    coptic_parent_tf=root / "nonexistent",
                    verify_parent_feature_hashes=False,
                )
            self.assertFalse((root / "modules").exists())

    def test_missing_parent_feature_blobs_fail_closed(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "missing.*LXX"):
                verify_lxx_parent_feature_blobs(Path(temp))


if __name__ == "__main__":
    unittest.main()
