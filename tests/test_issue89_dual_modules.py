"""RED-first native weft module contracts for Coptic↔LXX candidates (#89)."""
from __future__ import annotations

from hashlib import sha1
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from copticscriptorium_tf.lxx_modules import (
    LxxModuleError,
    git_blob_sha,
    render_node_feature,
    write_reference_modules,
)


class ModuleWeftContractTests(unittest.TestCase):
    def test_feature_is_a_native_tf_node_feature_with_sorted_nodes_and_provenance(self):
        payload = render_node_feature(
            "coptic_lxx_ref_id",
            {3: "CenterBLC/LXX:1935:Ruth:2:2", 1: "CenterBLC/LXX:1935:Ruth:2:1"},
            value_type="str",
            projection="coptic",
            description="matching address only, NOT established textual equivalence",
        )
        lines = payload.decode("utf-8").splitlines()
        self.assertEqual(lines[0], "@node")
        self.assertIn("@valueType=str", lines)
        self.assertIn("@copticUpstreamCommit=3ac067f1709a0012daf39ea8da2fac79980176a5", lines)
        self.assertIn("@lxxParentCommit=f32a98eddf7eb239aa73ab863d70381e416d5076", lines)
        self.assertLess(lines.index("1\tCenterBLC/LXX:1935:Ruth:2:1"), lines.index("3\tCenterBLC/LXX:1935:Ruth:2:2"))
        self.assertTrue(all(not line.startswith("@edge") for line in lines))
        self.assertNotIn(b'{"', payload)
        self.assertNotIn(b"<xml", payload)

    def test_rejects_invalid_node_ids_and_semantic_blobs(self):
        for values in ({0: "x"}, {-1: "x"}, {True: "x"}, {1: "x\ny"}, {1: "x\ty"}):
            with self.subTest(values=values):
                with self.assertRaises((LxxModuleError, ValueError)):
                    render_node_feature(
                        "coptic_lxx_ref_id", values, value_type="str",
                        projection="coptic", description="bad data",
                    )
        with self.assertRaises((LxxModuleError, ValueError)):
            render_node_feature(
                "otype", {1: "word"}, value_type="str",
                projection="coptic", description="warp spoof",
            )
        with self.assertRaises((LxxModuleError, ValueError)):
            render_node_feature(
                "coptic_lxx_source_span_count", {700000: 1}, value_type="int",
                projection="lxx", description="invalid parent node",
            )

    def test_adversarial_candidate_cannot_carry_unresolved_status(self):
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "no-forged-candidates"
            with self.assertRaisesRegex(LxxModuleError, "noncandidate status"):
                write_reference_modules(
                    target,
                    coptic_ref={1: "CenterBLC/LXX:1935:Ruth:2:1"},
                    coptic_status={1: "unresolved"},
                    lxx_ref={655362: "CenterBLC/LXX:1935:Ruth:2:1"},
                    lxx_count={655362: 1},
                )
            self.assertFalse(target.exists())

    def test_git_blob_fingerprint_checks_actual_bytes(self):
        data = b"@node\n@valueType=str\n\n1\tx\n"
        digest = sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "feature.tf"
            path.write_bytes(data)
            self.assertEqual(git_blob_sha(path), digest)

    def test_module_pair_no_clobber_and_no_warp(self):
        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "new-modules"
            write_reference_modules(
                destination,
                coptic_ref={1: "CenterBLC/LXX:1935:Ruth:2:1"},
                coptic_status={1: "reference_candidate", 2: "unresolved"},
                lxx_ref={655362: "CenterBLC/LXX:1935:Ruth:2:1"},
                lxx_count={655362: 1},
            )
            self.assertTrue((destination / "coptic/coptic_lxx_ref_id.tf").is_file())
            self.assertTrue((destination / "coptic/coptic_lxx_ref_status.tf").is_file())
            self.assertTrue((destination / "lxx/coptic_lxx_ref_id.tf").is_file())
            self.assertTrue((destination / "lxx/coptic_lxx_source_span_count.tf").is_file())
            self.assertFalse(list(destination.rglob("otype.tf")))
            self.assertFalse(list(destination.rglob("oslots.tf")))
            self.assertFalse(list(destination.rglob("*.json")))
            self.assertFalse(list(destination.rglob("*.tsv")))
            with self.assertRaises(FileExistsError):
                write_reference_modules(
                    destination,
                    coptic_ref={1: "CenterBLC/LXX:1935:Ruth:2:1"},
                    coptic_status={1: "reference_candidate"},
                    lxx_ref={655362: "CenterBLC/LXX:1935:Ruth:2:1"},
                    lxx_count={655362: 1},
                )


if __name__ == "__main__":
    unittest.main()
