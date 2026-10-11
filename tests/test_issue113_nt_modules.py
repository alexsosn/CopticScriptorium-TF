"""RED: bilateral NT verse-address wefts belong entirely to CopticScriptorium-TF."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from copticscriptorium_tf.nt_reference import GREEK_NT_EDITION
from copticscriptorium_tf.nt_modules import (
    NtModuleError, write_nt_modules, render_node_feature,
)

REF = f"{GREEK_NT_EDITION}:Mark:2:1"
PROOF = {
    "coptic": {"otype": "a" * 64, "oslots": "b" * 64},
    "greek": {"otype": "c" * 64, "oslots": "d" * 64,
              "book": "e" * 64, "chapter": "f" * 64, "verse": "0" * 64},
}


def write(path: Path, **changes):
    args = {
        "coptic_ref": {100: REF, 101: REF},
        "coptic_status": {100: "reference_candidate", 101: "reference_candidate",
                          102: "ambiguous"},
        "greek_ref": {800: REF},
        "greek_count": {800: 2},
        "parent_proof": PROOF,
    }
    args.update(changes)
    return write_nt_modules(path, **args)


class NativeNtWeftTests(unittest.TestCase):
    def test_both_native_warps_get_only_new_sparse_features(self):
        with TemporaryDirectory() as root:
            p = Path(root) / "modules"
            write(p)
            self.assertEqual(
                {f.name for f in (p/"coptic").iterdir()},
                {"coptic_nt_ref_id.tf", "coptic_nt_ref_status.tf"},
            )
            self.assertEqual(
                {f.name for f in (p/"greek").iterdir()},
                {"coptic_nt_ref_id.tf", "coptic_nt_source_occurrence_count.tf"},
            )
            coptic = (p/"coptic"/"coptic_nt_ref_status.tf").read_text()
            greek = (p/"greek"/"coptic_nt_source_occurrence_count.tf").read_text()
            self.assertIn("100\treference_candidate\n", coptic)
            self.assertIn("102\tambiguous\n", coptic)
            self.assertIn("800\t2\n", greek)
            self.assertIn("@copticParentOtypeSha256=" + "a"*64, coptic)
            self.assertIn("@greekParentOtypeSha256=" + "c"*64, greek)
            self.assertNotIn("oslots\t", greek)

    def test_existing_destination_fails_without_modification(self):
        with TemporaryDirectory() as root:
            p = Path(root) / "modules"
            write(p)
            before = (p/"coptic"/"coptic_nt_ref_id.tf").read_bytes()
            with self.assertRaises(FileExistsError):
                write(p)
            self.assertEqual(before, (p/"coptic"/"coptic_nt_ref_id.tf").read_bytes())

    def test_cannot_assign_foreign_or_missing_status_nodes(self):
        with TemporaryDirectory() as root:
            p = Path(root) / "weft"
            with self.assertRaisesRegex(NtModuleError, "status"):
                write(p, coptic_status={100: "reference_candidate"})
            self.assertFalse(p.exists())

    def test_wrong_edition_id_rejected(self):
        with TemporaryDirectory() as root:
            p = Path(root) / "weft"
            with self.assertRaisesRegex(NtModuleError, "edition"):
                write(p, coptic_ref={100: "morphgnt:other:Mark:2:1",
                                     101: REF})
            self.assertFalse(p.exists())

    def test_count_reconciles_all_coptic_occurrences_to_greek_address(self):
        with TemporaryDirectory() as root:
            p = Path(root) / "weft"
            with self.assertRaisesRegex(NtModuleError, "count"):
                write(p, greek_count={800: 1})
            with self.assertRaisesRegex(NtModuleError, "count"):
                write(p, greek_count={800: 3})
            self.assertFalse(p.exists())

    def test_unmatched_parent_address_fails(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(NtModuleError, "reference"):
                write(Path(root)/"weft", greek_ref={800: REF.replace(":2:1", ":2:2")})

    def test_no_json_xml_newlines_or_forged_node_ids(self):
        for invalid in (REF + "\nblat", REF + "\t1337", "<xml/>"):
            with self.subTest(invalid=invalid), TemporaryDirectory() as root:
                with self.assertRaises(NtModuleError):
                    write(Path(root)/"weft", coptic_ref={100:invalid,101:REF})
        with TemporaryDirectory() as root:
            with self.assertRaises(NtModuleError):
                write(Path(root)/"weft", greek_ref={True:REF})

    def test_invalid_parent_fingerprint_is_fail_closed(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(NtModuleError, "fingerprint"):
                write(Path(root)/"weft", parent_proof={
                    "coptic": {"otype":"wrong", "oslots":"b"*64},
                    "greek": PROOF["greek"],
                })

    def test_status_without_reference_remains_visible(self):
        with TemporaryDirectory() as root:
            p=Path(root)/"weft"
            write(p, coptic_status={
                100:"reference_candidate",101:"reference_candidate",
                102:"unresolved",103:"edition_unavailable",
                104:"unclassified_source",105:"ambiguous",
            })
            content=(p/"coptic"/"coptic_nt_ref_status.tf").read_text()
            for status in ("unresolved","edition_unavailable","unclassified_source","ambiguous"):
                self.assertIn(status,content)

if __name__ == "__main__":
    unittest.main()
