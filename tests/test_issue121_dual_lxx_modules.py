"""RED-first native Text-Fabric dual projection contracts for issue #121."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from copticscriptorium_tf.lxx_reference import CopticLxxReference
from copticscriptorium_tf.lxx_modules import (
    CopticReferencePlacement,
    compile_dual_reference_features,
    write_dual_reference_modules,
)


def ref(record, ords, verse, greek_node, status="reference_candidate"):
    return CopticLxxReference(
        source_record_id=record,
        source_word_ordinals=tuple(ords),
        source_verse_n=str(verse),
        source_vid_n=None,
        source_verse_vid=None,
        lxx_book="Ruth",
        lxx_chapter=2,
        lxx_verse=verse,
        lxx_node=greek_node,
        shared_id=f"CenterBLC/LXX:1935:Ruth:2:{verse}" if greek_node else None,
        status=status,
        evidence="verse_n",
        reason="verified Greek address; textual equivalence not established",
    )


class DualNativeReferenceTests(unittest.TestCase):
    def test_many_coptic_witnesses_share_one_greek_verse_without_cross_warp_links(self):
        projections = (
            CopticReferencePlacement((1, 2), ref("sahidic.ruth/ruth:a", (1, 2), 1, 100)),
            CopticReferencePlacement((3,), ref("sahidic.ruth/ruth:b", (1,), 1, 100)),
            CopticReferencePlacement((4,), ref("sahidic.ruth/ruth:b", (2,), 2, None, "unresolved")),
        )
        coptic, greek = compile_dual_reference_features(
            projections, coptic_max_slot=20, lxx_max_node=500
        )
        self.assertEqual(coptic["clxx_ref_id"], {
            1: "CenterBLC/LXX:1935:Ruth:2:1",
            2: "CenterBLC/LXX:1935:Ruth:2:1",
            3: "CenterBLC/LXX:1935:Ruth:2:1",
        })
        self.assertEqual(greek["clxx_ref_id"], {100: "CenterBLC/LXX:1935:Ruth:2:1"})
        self.assertEqual(greek["clxx_coptic_witness_n"], {100: 2})
        self.assertEqual(greek["clxx_coptic_word_n"], {100: 3})
        self.assertEqual(coptic["clxx_ref_status"][4], "unresolved")
        self.assertNotIn(4, coptic["clxx_ref_id"])
        self.assertFalse(any("edge" in name or "target_node" in name for name in coptic))

    def test_repeated_source_word_or_inconsistent_greek_reference_rejected(self):
        twice = (
            CopticReferencePlacement((1,), ref("a", (1,), 1, 100)),
            CopticReferencePlacement((1,), ref("a", (1,), 1, 100)),
        )
        with self.assertRaisesRegex(ValueError, "duplicate Coptic word"):
            compile_dual_reference_features(twice, coptic_max_slot=3, lxx_max_node=500)
        different_id_same_verse_node = (
            CopticReferencePlacement((1,), ref("a", (1,), 1, 100)),
            CopticReferencePlacement((2,), ref("b", (1,), 2, 100)),
        )
        with self.assertRaisesRegex(ValueError, "Greek verse reference collision"):
            compile_dual_reference_features(
                different_id_same_verse_node, coptic_max_slot=3, lxx_max_node=500
            )
        with self.assertRaisesRegex(ValueError, "invalid Greek verse"):
            compile_dual_reference_features(
                (CopticReferencePlacement((1,), ref("a", (1,), 1, 1000)),),
                coptic_max_slot=3, lxx_max_node=500
            )

    def test_weft_only_module_files_and_exact_provenance(self):
        p = (CopticReferencePlacement((1,), ref("a", (1,), 1, 100)),)
        coptic, greek = compile_dual_reference_features(
            p, coptic_max_slot=3, lxx_max_node=500
        )
        with TemporaryDirectory() as tmp:
            destination = Path(tmp) / "bundle"
            write_dual_reference_modules(
                destination, coptic=coptic, lxx=greek,
                coptic_upstream_commit="3ac067f1709a0012daf39ea8da2fac79980176a5",
                lxx_release_commit="f32a98eddf7eb239aa73ab863d70381e416d5076",
            )
            for part in ("coptic", "lxx"):
                directory = destination / part
                self.assertTrue((directory / "clxx_ref_id.tf").exists())
                self.assertFalse({p.stem for p in directory.glob("*.tf")} & {"otype","oslots","otext"})
                content = (directory / "clxx_ref_id.tf").read_text()
                self.assertIn("@clxxSchema=1", content)
                self.assertIn("@parentCommit=", content)
                self.assertIn("@sourceCommit=3ac067f1709a0012daf39ea8da2fac79980176a5", content)
                self.assertIn("@lxxReleaseCommit=f32a98eddf7eb239aa73ab863d70381e416d5076", content)
            with self.assertRaises(FileExistsError):
                write_dual_reference_modules(
                    destination, coptic=coptic, lxx=greek,
                    coptic_upstream_commit="3ac067f1709a0012daf39ea8da2fac79980176a5",
                    lxx_release_commit="f32a98eddf7eb239aa73ab863d70381e416d5076",
                )


if __name__ == "__main__":
    unittest.main()
