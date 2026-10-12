"""RED: only exact original pinned 1Cor1:9 truncated CTS evidence is eligible."""
from dataclasses import replace
import unittest

from copticscriptorium_tf.nt_reference import (
    _pinned_1cor1_short_vid, _git_blob_for_document,
    _source_model_matches_original_tt,
    resolve_coptic_sbl_references,
)
from copticscriptorium_tf.parser import parse_tt_record
from test_issue113_nt_reference import make_doc, PIN

BLOB = "87b0c52de46be063c34aa343160103fa9603758a"
CANONICAL = "sahidica.1corinthians/sahidica.1corinthians:1Cor_01"
TREEBANK = "coptic-treebank/coptic.treebank:1Cor_01"


def proven(*, record=CANONICAL, blob=BLOB, ordinal=12,
           kind="sbl_greek", chapter=1, verse=9,
           vid=".9", label="46N 1:9"):
    return _pinned_1cor1_short_vid(
        record=record, source_git_blob=blob,
        ordinal=ordinal, kind=kind, chapter=chapter, verse=verse,
        vid=vid, label=label,
    )


class TruncatedOneCorinthiansCts(unittest.TestCase):
    def test_both_physical_source_witnesses_allowed_by_exact_provenance(self):
        self.assertTrue(proven())
        self.assertTrue(proven(record=TREEBANK))

    def test_other_source_or_malformed_marker_is_not_whitelisted(self):
        cases = [
            {"record": CANONICAL.replace("1Cor_01","1Cor_02")},
            {"record": "sahidica.mark/sahidica.mark:Mark_01"},
            {"record": "coptic-treebank/forged:1Cor_01"},
            {"blob": "0"*40},
            {"ordinal": 11}, {"ordinal": 13},
            {"kind": "sbl_apparatus"},
            {"chapter": 2}, {"chapter": 0},
            {"verse": 8}, {"verse": 10},
            {"vid": ".8"}, {"vid": ".10"}, {"vid": "garbage"},
            {"label": "46N 1:10"}, {"label": "41N 1:9"},
            {"label": None},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertFalse(proven(**changes))

    def test_forged_source_bytes_never_qualify_even_with_claimed_git_commit(self):
        d = make_doc(book="1Cor", work="1cor", code="46N",
                     chapter=1, verse=9)
        original = d.source_text
        mutated = original.replace(
            "urn:cts:copticLit:nt.1cor.sahidica_ed:1.9", ".9"
        )
        self.assertNotEqual(mutated, original)
        doc = parse_tt_record(
            mutated.encode("utf-8"), source_record_id=CANONICAL,
            source_path="sahidica.1corinthians/sahidica.1corinthians_TT/1Cor_01.tt",
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        c, = resolve_coptic_sbl_references(doc, lookup=lambda *ref: 12345)
        self.assertEqual(c.status, "ambiguous")
        self.assertIsNone(c.target_node)
        self.assertEqual(c.source_vid_n, ".9")

    def test_canonical_source_model_reparse_rejects_forged_annotation_and_words(self):
        d=make_doc(book="1Cor",work="1cor",code="46N",chapter=1,verse=9)
        self.assertTrue(_source_model_matches_original_tt(d))
        bad_ann=replace(d.sbl_annotations[0],value="forged annotation")
        self.assertFalse(_source_model_matches_original_tt(
            replace(d,sbl_annotations=(bad_ann,))))
        bad_word=replace(d.words[0],norm="forged Coptic token")
        self.assertFalse(_source_model_matches_original_tt(
            replace(d,words=(bad_word,))))
        self.assertFalse(_source_model_matches_original_tt(
            replace(d,metadata={**d.metadata,"book":"Mark"})))

    def test_source_text_mutation_without_digest_is_detected(self):
        d=make_doc(book="1Cor",work="1cor",code="46N",chapter=1,verse=9)
        forged=replace(
            d, source_record_id=CANONICAL,
            source_text=d.source_text.replace("1.9", ".9"),
        )
        with self.assertRaisesRegex(ValueError, "source bytes"):
            _git_blob_for_document(forged)

    def test_exact_git_blob_digest_matches_original_source_text_not_claimed_revision(self):
        d = make_doc(book="1Cor",work="1cor",code="46N",
                     chapter=1,verse=9)
        self.assertNotEqual(_git_blob_for_document(d), BLOB)
        self.assertEqual(len(_git_blob_for_document(d)), 40)


if __name__ == "__main__":
    unittest.main()
