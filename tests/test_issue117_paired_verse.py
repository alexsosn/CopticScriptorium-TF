"""RED: independently paired human/editor verse labels in original 1Cor14 TT.

Do not synthesize verse_n, infer Greek text equality or weaken Mark/other
source evidence. Every word in the original SBL wrapper must be covered by
both matching *independent* source verse labels.
"""
from dataclasses import replace
import unittest

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.nt_reference import resolve_coptic_sbl_references

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
PHYSICAL = "sahidica.1corinthians/sahidica.1corinthians:1Cor_14"


def doc(*, verse="1 Corinthians 14:3", editor="46N 14:3",
        second_verse=None, second_editor=None, greek_source=True,
        chapter="14", source_record=PHYSICAL, outside=False, kind="sbl_greek"):
    provenance = "Greek source SBL Greek New Testament 2010" if greek_source else ""
    opening = (
        f'<meta corpus="sahidica.1corinthians" book="1Cor" chapter="{chapter}" '
        f'document_cts_urn="urn:cts:copticLit:nt.1cor.sahidica_ed:{chapter}" '
        f'Greek_source="{provenance}">'
    )
    first = (
        f'<{kind} {kind}="source Greek">'
        f'<verse_vid verse_vid="{editor}"><verse verse="{verse}">'
        '<norm_group norm_group="a"><norm xml:id="u1" norm="ⲁ" new_sent="true">ⲁ</norm></norm_group>'
        '</verse></verse_vid>'
    )
    if second_verse is not None:
        first += (
            f'<verse_vid verse_vid="{second_editor or editor}">'
            f'<verse verse="{second_verse}">'
            '<norm_group norm_group="b"><norm xml:id="u2" norm="ⲃ">ⲃ</norm></norm_group>'
            '</verse></verse_vid>'
        )
    first += f'</{kind}>'
    if outside:
        first = first.replace(
            '<verse verse=', '<verse verse=', 1
        ).replace("</verse></verse_vid>", "</verse></verse_vid>", 1)
    return parse_tt_record((opening+first).encode(),
        source_record_id=source_record,
        source_path="sahidica.1corinthians/sahidica.1corinthians_TT/1Cor_14.tt",
        upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN)


class PairedSourceVerseEvidence(unittest.TestCase):
    def test_agreeing_two_labels_yield_book_qualified_candidate(self):
        d=doc()
        keys=[]
        r,=resolve_coptic_sbl_references(d,lookup=lambda *args:keys.append(args) or 456789)
        self.assertEqual(keys,[("1_Corinthians",14,3)])
        self.assertEqual(r.status,"reference_candidate")
        self.assertEqual(r.target_node,456789)
        self.assertEqual((r.target_chapter,r.target_verse),(14,3))
        self.assertIsNone(r.source_verse_n)
        self.assertEqual(r.source_verse_vid,"46N 14:3")
        self.assertIn("verse+verse_vid",r.evidence)

    def test_apparatus_occurrence_is_eligible_only_with_whole_word_pair(self):
        r,=resolve_coptic_sbl_references(doc(kind="sbl_apparatus"),
            lookup=lambda *args:101)
        self.assertEqual(r.status,"reference_candidate")
        self.assertEqual(r.source_kind,"sbl_apparatus")

    def test_broken_label_cannot_map(self):
        cases = [
            {"verse":"1 Corinthians 14:4"},
            {"verse":"Mark 14:3"},
            {"verse":"1 Corinthians 13:3"},
            {"editor":"46N 14:4"},
            {"editor":"41N 14:3"},
            {"verse":"anything"},
            {"verse":""},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                calls=[]
                r,=resolve_coptic_sbl_references(doc(**kwargs),
                    lookup=lambda *args:calls.append(args) or 4)
                self.assertNotEqual(r.status,"reference_candidate")
                self.assertEqual(calls,[])
                self.assertIsNone(r.shared_id)

    def test_span_crossing_two_source_verses_fails_closed(self):
        d=doc(second_verse="1 Corinthians 14:4",second_editor="46N 14:4")
        self.assertEqual(len(d.words),2)
        r,=resolve_coptic_sbl_references(d,lookup=lambda *args:111)
        self.assertEqual(r.status,"ambiguous")
        self.assertIsNone(r.target_node)

    def test_physical_record_and_provenance_are_required(self):
        for d in (
            doc(greek_source=False),
            doc(source_record=PHYSICAL.replace("1Cor_14","1Cor_13")),
            doc(chapter="13"),
            replace(doc(),upstream_commit="forged"),
        ):
            with self.subTest(record=d.source_record_id,sha=d.upstream_commit):
                if d.upstream_commit != PIN:
                    with self.assertRaisesRegex(ValueError,"revision"):
                        resolve_coptic_sbl_references(d,lookup=lambda *a:18)
                else:
                    r,=resolve_coptic_sbl_references(d,lookup=lambda *a:18)
                    self.assertNotEqual(r.status,"reference_candidate")

    def test_not_permitted_in_other_books_chapters(self):
        d=doc(source_record="sahidica.1corinthians/sahidica.1corinthians:1Cor_13")
        r,=resolve_coptic_sbl_references(d,lookup=lambda *args:23)
        self.assertNotEqual(r.status,"reference_candidate")

    def test_reject_modified_raw_label_stream_without_matching_original_source_hash(self):
        d=doc()
        tampered=replace(
            d,
            source_text=d.source_text.replace(
                '<verse verse="1 Corinthians 14:3">',
                '<verse verse="1 Corinthians 14:4">',
            ),
        )
        with self.assertRaisesRegex(ValueError,"source bytes"):
            resolve_coptic_sbl_references(tampered,lookup=lambda *args:17)

    def test_reject_duplicate_source_verse_attribute(self):
        original=doc()
        changed=original.source_text.replace(
            '<verse verse="1 Corinthians 14:3">',
            '<verse verse="1 Corinthians 14:3" verse="1 Corinthians 14:4">',
        )
        reloaded=parse_tt_record(changed.encode(),source_record_id=PHYSICAL,
            source_path=original.source_path,
            upstream_repository="CopticScriptorium/corpora",upstream_commit=PIN)
        with self.assertRaisesRegex(ValueError,"duplicate"):
            resolve_coptic_sbl_references(reloaded,lookup=lambda *a:1)

    def test_verse_boundary_inside_coptic_norm_never_maps(self):
        original=doc()
        changed=original.source_text.replace(
            '<norm xml:id="u1" norm="ⲁ" new_sent="true">ⲁ</norm>',
            '<norm xml:id="u1" norm="ⲁ" new_sent="true">'
            'ⲁ</verse></verse_vid><verse_vid verse_vid="46N 14:3">'
            '<verse verse="1 Corinthians 14:3"></norm>',
        )
        reloaded=parse_tt_record(changed.encode(),source_record_id=PHYSICAL,
            source_path=original.source_path,
            upstream_repository="CopticScriptorium/corpora",upstream_commit=PIN)
        calls=[]
        r,=resolve_coptic_sbl_references(reloaded,
            lookup=lambda *a:calls.append(a) or 1)
        self.assertNotEqual(r.status,"reference_candidate")
        self.assertEqual(calls,[])

    def test_invalid_word_ordinal_fails_closed(self):
        d=doc()
        annotation=replace(d.sbl_annotations[0],word_ordinals=(True,))
        r,=resolve_coptic_sbl_references(
            replace(d,sbl_annotations=(annotation,)),lookup=lambda *args:17)
        self.assertNotEqual(r.status,"reference_candidate")

    def test_missing_explicit_pair_does_not_fabricate_verse(self):
        original=doc()
        changed=original.source_text.replace(
            '<verse verse="1 Corinthians 14:3">', '<verse verse="wrong">'
        )
        # Reparse the modified synthetic source, so its own SHA256 is honest.
        # A different test rejects forged source_text without rehashing.
        d=parse_tt_record(changed.encode(),source_record_id=PHYSICAL,
            source_path=original.source_path,
            upstream_repository="CopticScriptorium/corpora",upstream_commit=PIN)
        calls=[]
        r,=resolve_coptic_sbl_references(d,lookup=lambda *args:calls.append(args) or 19)
        self.assertEqual(r.status,"ambiguous")
        self.assertEqual(calls,[])


if __name__=="__main__":
    unittest.main()
