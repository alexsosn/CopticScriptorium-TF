"""RED-first #75: per-work metadata coverage, not LXX alignment."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import unittest

from tests.live_issue75_ot_inventory import (
    inventory_source_tree,
    summarize_ot_work_profiles,
)


def tt(meta: str, verse: int = 1) -> str:
    return (
        f"<meta {meta}><verse_n verse_n=\"1\">"
        f"<norm_group norm_group=\"w\"><norm xml:id=\"u1\" new_sent=\"true\" "
        f"func=\"root\" norm=\"a\">a</norm></norm_group>"
    )


class BookCoverageMatrixTests(unittest.TestCase):
    def test_distinct_cts_works_and_missing_reference_not_merged_in_ot_zip(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ot = root / "sahidic.ot" / "sahidic.ot_TT.zip"
            ot.parent.mkdir()
            with ZipFile(ot, "w") as z:
                z.writestr("Ruth_02.tt", tt(
                    'chapter="2" book="Ruth" document_cts_urn="urn:cts:copticLit:ot.ruth.ed:2"'
                ))
                z.writestr("Jonah_02.tt", tt(
                    'chapter="2" document_cts_urn="urn:cts:copticLit:ot.jonah.ed:2"'
                ))
                z.writestr("Unknown.tt", tt('chapter="3"'))
            direct = root / "bohairic-habakkuk" / "bohairic.habakkuk_TT" / "Hab_02.tt"
            direct.parent.mkdir(parents=True)
            direct.write_text(tt('book="Habakkuk" chapter="02"'), encoding="utf-8")
            nt = root / "sahidica.nt" / "sahidica.nt_TT.zip"
            nt.parent.mkdir()
            with ZipFile(nt, "w") as z:
                z.writestr("Mark_02.tt", tt(
                    'book="Mark" chapter="2" document_cts_urn="urn:cts:copticLit:nt.mark.ed:2"'
                ))

            report = inventory_source_tree(root, expected_blobs=3, expected_records=5)
            profiles = report["source_families"]["sahidic.ot"]["source_work_profiles"]
            self.assertEqual(sorted(profiles), ["cts:ot.jonah", "cts:ot.ruth", "unknown"])
            self.assertEqual(sum(v["source_records"] for v in profiles.values()), 3)
            ruth = profiles["cts:ot.ruth"]
            self.assertEqual(ruth["source_records"], 1)
            self.assertEqual(ruth["reference_evidence_counts"], {"cts": 1})
            self.assertEqual(ruth["chapter_literal_counts"], {"2": 1})
            self.assertEqual(ruth["literal_book_counts"], {"Ruth": 1})
            self.assertEqual(ruth["scope_counts"], {"ot_candidate": 1})
            self.assertEqual(ruth["verse_markers"], 1)
            unknown = profiles["unknown"]
            self.assertEqual(unknown["reference_evidence_counts"], {"unknown": 1})
            self.assertEqual(unknown["chapter_literal_counts"], {"3": 1})
            self.assertEqual(unknown["scope_counts"], {"ot_candidate": 1})
            hab = report["source_families"]["bohairic-habakkuk"]["source_work_profiles"]
            self.assertEqual(tuple(hab), ("book:Habakkuk",))
            self.assertEqual(hab["book:Habakkuk"]["reference_evidence_counts"], {"book": 1})
            self.assertEqual(hab["book:Habakkuk"]["chapter_literal_counts"], {"02": 1})

            ot_rows = summarize_ot_work_profiles(report)
            self.assertEqual(sum(row["source_records"] for row in ot_rows), 4)
            self.assertEqual(
                {(row["source_family"], row["source_work_key"]) for row in ot_rows},
                {("sahidic.ot", "cts:ot.ruth"), ("sahidic.ot", "cts:ot.jonah"),
                 ("sahidic.ot", "unknown"),
                 ("bohairic-habakkuk", "book:Habakkuk")},
            )
            self.assertNotIn("sahidica.nt", repr(ot_rows))
            self.assertEqual(ot_rows, summarize_ot_work_profiles(report))
            self.assertTrue(all("text" not in str(x).lower() for x in ot_rows))
            self.assertTrue(all(len(row["examples"]) <= 3 for row in ot_rows))


if __name__ == "__main__":
    unittest.main()
