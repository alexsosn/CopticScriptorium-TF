"""RED: NT source SBL wrappers are verse evidence, never Greek token alignment."""
from dataclasses import replace
import unittest

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.nt_reference import (
    GREEK_NT_EDITION, resolve_coptic_sbl_references, morphgnt_verse_is_absent,
)

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
PROVENANCE = "Greek text annotated as sbl_greek and sbl_apparatus are from the SBL Greek New Testament (c)2010."

def make_doc(
    *, book="Mark", work="mark", code="41N", chapter=2, verse=1,
    cts_verse=None, label_verse=None, word_verse=None, greek_source=PROVENANCE,
    greek="⸀λόγος· ", annot_kind="sbl_greek", extra_word=False,
    verse_literal=None, include_vid_n=True,
):
    cts_verse = verse if cts_verse is None else cts_verse
    label_verse = verse if label_verse is None else label_verse
    word_verse = verse if word_verse is None else word_verse
    family = "sahidica.1corinthians" if book == "1Cor" else ("sahidica.john" if book == "John" else "sahidica.mark")
    meta = (f'<meta corpus="{family}" book="{book}" chapter="{chapter}" '
            f'document_cts_urn="urn:cts:copticLit:nt.{work}.sahidica_ed:{chapter}" '
            f'Greek_source="{greek_source}">')
    annotation = (
        f'<verse_n verse_n="{word_verse if verse_literal is None else verse_literal}"><{annot_kind} {annot_kind}="{greek}">'
        f'<verse_vid verse_vid="{code} {chapter}:{label_verse}">'
        (f'<vid_n vid_n="urn:cts:copticLit:nt.{work}.sahidica_ed:{chapter}.{cts_verse}">' if include_vid_n else "")
        '<norm_group norm_group="a"><norm xml:id="u1" new_sent="true" func="root" norm="ⲁ">ⲁ</norm></norm_group>'
    )
    if extra_word:
        annotation += '<norm_group norm_group="b"><norm xml:id="u2" func="root" norm="ⲃ">ⲃ</norm></norm_group>'
    annotation += f'</{annot_kind}>' + ('</vid_n>' if include_vid_n else '') + '</verse_vid></verse_n>'
    return parse_tt_record((meta+annotation).encode("utf-8"),
        source_record_id=f"{family}/{family}:Chapter_02",
        source_path=f"{family}/{family}_TT/Chapter_02.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN)

class GreekNtReferences(unittest.TestCase):
    def test_mark_real_markup_style_proposes_edition_qualified_verse(self):
        d = make_doc(extra_word=True)
        candidates = resolve_coptic_sbl_references(
            d, lookup=lambda b,c,v: 100_001 if (b,c,v)==("Mark",2,1) else None)
        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertEqual(c.status, "reference_candidate")
        self.assertEqual(c.source_word_ordinals, (1,2))
        self.assertEqual(c.target_book, "Mark")
        self.assertEqual(c.target_node, 100_001)
        self.assertEqual(c.shared_id, f"{GREEK_NT_EDITION}:Mark:2:1")
        self.assertEqual(c.source_kind, "sbl_greek")
        self.assertEqual(c.source_ordinal, 1)
        self.assertEqual(c.evidence, "book+chapter+document_cts_urn+verse_n+vid_n+verse_vid+sbl_greek")

    def test_treebank_duplicate_physical_mark_witness_uses_original_meta_family(self):
        d=make_doc()
        d=replace(d,corpus="coptic-treebank",dataset="coptic.treebank",
                  source_record_id="coptic-treebank/coptic.treebank:Mark_02")
        c,=resolve_coptic_sbl_references(d,lookup=lambda b,c,v:111)
        self.assertEqual(c.status,"reference_candidate")
        self.assertEqual(c.source_record_id,"coptic-treebank/coptic.treebank:Mark_02")

    def test_treebank_forged_meta_corpus_is_not_reviewed(self):
        d=make_doc()
        d=replace(d,corpus="coptic-treebank",dataset="coptic.treebank",
                  source_record_id="coptic-treebank/coptic.treebank:Mark_02",
                  metadata={**d.metadata,"corpus":"unrelated"})
        calls=[]
        c,=resolve_coptic_sbl_references(d,lookup=lambda *key:calls.append(key) or 111)
        self.assertEqual(c.status,"unclassified_source")
        self.assertEqual(calls,[])

    def test_duplicate_conflicting_identity_metadata_not_accepted(self):
        d=make_doc()
        d=replace(d,metadata_duplicates={
            **d.metadata_duplicates,"book":("Mark","John")
        })
        calls=[]
        c,=resolve_coptic_sbl_references(d,lookup=lambda *key:calls.append(key) or 111)
        self.assertEqual(c.status,"ambiguous")
        self.assertEqual(calls,[])

    def test_wrong_physical_dataset_not_trusted_as_reviewed_source(self):
        d=make_doc()
        d=replace(d,dataset="forged",source_record_id="sahidica.mark/forged:Mark_02")
        calls=[]
        c,=resolve_coptic_sbl_references(d,lookup=lambda *key:calls.append(key) or 111)
        self.assertEqual(c.status,"unclassified_source")
        self.assertEqual(calls,[])

    def test_real_1cor_chapter3_qualified_source_verse_label(self):
        d = make_doc(book="1Cor", work="1cor", code="46N", chapter=3,
                     verse=1, verse_literal="1 Corinthians 3:1")
        c, = resolve_coptic_sbl_references(d, lookup=lambda *ref: 19)
        self.assertEqual(c.status, "reference_candidate")
        self.assertEqual((c.target_book, c.target_chapter, c.target_verse),
                         ("1_Corinthians", 3, 1))

    def test_real_mark8_missing_vid_n_can_use_consistent_other_references(self):
        d = make_doc(book="Mark", work="mark", code="41N", chapter=8,
                     verse=1, include_vid_n=False)
        c, = resolve_coptic_sbl_references(d, lookup=lambda *ref: 19)
        self.assertEqual(c.status, "reference_candidate")
        self.assertNotIn("vid_n+", c.evidence)
        self.assertIsNone(c.source_vid_n)

    def test_missing_vid_with_wrong_editor_verse_cannot_map(self):
        d = make_doc(chapter=8, verse=1, include_vid_n=False, label_verse=2)
        calls = []
        c, = resolve_coptic_sbl_references(d, lookup=lambda *ref: calls.append(ref) or 19)
        self.assertEqual(c.status, "ambiguous")
        self.assertEqual(calls, [])

    def test_forged_human_readable_verse_book_is_rejected(self):
        d = make_doc(book="1Cor", work="1cor", code="46N", chapter=3,
                     verse=1, verse_literal="John 3:1")
        calls = []
        c, = resolve_coptic_sbl_references(d, lookup=lambda *ref: calls.append(ref) or 19)
        self.assertEqual(c.status, "ambiguous")
        self.assertEqual(calls, [])

    def test_verse_label_wrong_chapter_is_rejected(self):
        d = make_doc(book="1Cor", work="1cor", code="46N", chapter=3,
                     verse=1, verse_literal="1 Corinthians 2:1")
        c, = resolve_coptic_sbl_references(d, lookup=lambda *ref: 19)
        self.assertEqual(c.status, "ambiguous")

    def test_1cor_real_alias_uses_parent_canonical_book(self):
        d = make_doc(book="1Cor",work="1cor",code="46N",annot_kind="sbl_apparatus")
        c, = resolve_coptic_sbl_references(d,lookup=lambda b,c,v: 19 if (b,c,v)==("1_Corinthians",2,1) else None)
        self.assertEqual(c.status, "reference_candidate")
        self.assertEqual(c.target_book, "1_Corinthians")
        self.assertEqual(c.source_kind, "sbl_apparatus")

    def test_known_missing_edition_passage_never_maps_unreviewed_source(self):
        self.assertTrue(morphgnt_verse_is_absent("John", 7, 53))
        self.assertTrue(morphgnt_verse_is_absent("John", 8, 11))
        self.assertFalse(morphgnt_verse_is_absent("John", 8, 12))
        d = make_doc(book="John",work="john",code="43N",chapter=7,verse=53)
        calls=[]
        c, = resolve_coptic_sbl_references(d,lookup=lambda *key: calls.append(key) or 10)
        self.assertEqual(c.status, "unclassified_source")
        self.assertIsNone(c.shared_id)
        self.assertEqual(calls, [])

    def test_noncanonical_missing_verse_is_unresolved_not_whitelisted(self):
        d = make_doc()
        c, = resolve_coptic_sbl_references(d,lookup=lambda *key: None)
        self.assertEqual(c.status,"unresolved")

    def test_crossed_or_mixed_verse_span_never_maps(self):
        d=make_doc(extra_word=True)
        w=list(d.words)
        w[1]=replace(w[1],verse_n="2")
        d=replace(d,words=tuple(w))
        calls=[]
        c,=resolve_coptic_sbl_references(d,lookup=lambda *key: calls.append(key) or 99)
        self.assertEqual(c.status,"ambiguous")
        self.assertEqual(calls,[])

    def test_conflicting_source_verse_label_blocks_lookup(self):
        d=make_doc(label_verse=2)
        called=[]
        c,=resolve_coptic_sbl_references(d,lookup=lambda *key:called.append(key) or 12)
        self.assertEqual(c.status,"ambiguous")
        self.assertEqual(called,[])

    def test_missing_greek_provenance_never_maps(self):
        d=make_doc(greek_source="")
        calls=[]
        c,=resolve_coptic_sbl_references(d,lookup=lambda *key:calls.append(key) or 13)
        self.assertEqual(c.status,"unclassified_source")
        self.assertEqual(calls,[])

    def test_forged_foreign_cts_work_rejected(self):
        d=make_doc(work="jonah")
        calls=[]
        c,=resolve_coptic_sbl_references(d,lookup=lambda *key:calls.append(key) or 13)
        self.assertEqual(c.status,"ambiguous")
        self.assertEqual(calls,[])

    def test_unsupported_books_are_visible_unclassified(self):
        d=make_doc(book="Luke",work="luke",code="42N")
        c,=resolve_coptic_sbl_references(d,lookup=lambda *key:14)
        self.assertEqual(c.status,"unclassified_source")

    def test_empty_span_is_unresolved_not_forged_word_verse(self):
        d=make_doc()
        annotation=replace(d.sbl_annotations[0],word_ordinals=())
        d=replace(d,sbl_annotations=(annotation,))
        c,=resolve_coptic_sbl_references(d,lookup=lambda *key:12)
        self.assertEqual(c.status,"unresolved")
        self.assertIsNone(c.shared_id)

    def test_ordinal_and_annotation_source_value_not_a_word_alignment(self):
        d=make_doc(greek="wrong Greek spelling")
        c,=resolve_coptic_sbl_references(d,lookup=lambda *key:87)
        self.assertEqual(c.status,"reference_candidate")
        self.assertEqual(c.source_word_ordinals,(1,))
        self.assertFalse(hasattr(c,"greek_word_ordinal"))

    def test_wrong_pin_and_invalid_lookup_rejected(self):
        d=make_doc()
        with self.assertRaisesRegex(ValueError,"source revision"):
            resolve_coptic_sbl_references(replace(d,upstream_commit="bad"), lookup=lambda *x: 10)
        with self.assertRaisesRegex(ValueError,"positive"):
            resolve_coptic_sbl_references(d, lookup=lambda *x: True)

    def test_none_for_unannotated_document(self):
        d=make_doc()
        self.assertEqual(resolve_coptic_sbl_references(replace(d,sbl_annotations=()),lookup=lambda *x:9),())

if __name__ == "__main__":
    unittest.main()
