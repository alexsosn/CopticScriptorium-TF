"""RED-first: Mark1 CTS word marker corroboration without editorial verse_vid.

Only reviewed Mark_01 physical witnesses may use this alternative. Neither
source Greek text nor Coptic words are considered token correspondences.
"""
from dataclasses import replace
import unittest

from copticscriptorium_tf.nt_reference import resolve_coptic_sbl_references
from copticscriptorium_tf.parser import parse_tt_record

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
CANON = "sahidica.mark/sahidica.mark:Mark_01"
TREE = "coptic-treebank/coptic.treebank:Mark_01"


def document(*, record=CANON, verse=3, vid_verse=None, include_vid=True,
             greek="πηγή", kind="sbl_greek", editor=None, provenance=True,
             chapter=1, extra_word=False):
    if vid_verse is None:
        vid_verse = verse
    physical = record.split("/")[0]
    dataset = "coptic.treebank" if physical == "coptic-treebank" else "sahidica.mark"
    meta = (
        f'<meta book="Mark" chapter="{chapter}" corpus="sahidica.mark" '
        f'document_cts_urn="urn:cts:copticLit:nt.mark.sahidica_ed:{chapter}" '
        f'Greek_source="{"SBL Greek New Testament" if provenance else ""}">'
    )
    verse_open = f'<verse_n verse_n="{verse}">'
    editor_open = f'<verse_vid verse_vid="{editor}">' if editor else ""
    vid_open = (
        f'<vid_n vid_n="urn:cts:copticLit:nt.mark.sahidica_ed:{chapter}.{vid_verse}">'
        if include_vid else ""
    )
    text = (
        f'{meta}{verse_open}{editor_open}{vid_open}'
        f'<{kind} {kind}="{greek}">'
        '<norm_group norm_group="ⲁ">'
        '<norm xml:id="u1" norm="ⲁ" func="root">ⲁ</norm>'
        '</norm_group>'
    )
    if extra_word:
        text += '<norm_group norm_group="ⲃ"><norm xml:id="u2" norm="ⲃ">ⲃ</norm></norm_group>'
    text += f'</{kind}>'
    text += "</vid_n>" if include_vid else ""
    text += "</verse_vid>" if editor else ""
    text += "</verse_n>"
    return parse_tt_record(text.encode("utf-8"),
        source_record_id=record,
        source_path=f"{physical}/{dataset}_TT/Mark_01.tt",
        upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN)


def resolved(doc):
    called = []
    result, = resolve_coptic_sbl_references(
        doc, lookup=lambda *args: called.append(args) or 99123
    )
    return result, called


class Mark1SourceCTS(unittest.TestCase):
    def test_two_scoped_verse_markers_on_canonical_source(self):
        result, called = resolved(document())
        self.assertEqual(result.status, "reference_candidate")
        self.assertEqual(called, [("Mark", 1, 3)])
        self.assertIn("verse_n+vid_n", result.evidence)
        self.assertNotIn("verse_vid", result.evidence)
        self.assertEqual(result.target_verse, 3)

    def test_separate_treebank_physical_source_is_allowed(self):
        result, called = resolved(document(record=TREE, kind="sbl_apparatus"))
        self.assertEqual(result.status, "reference_candidate")
        self.assertEqual(result.source_record_id, TREE)
        self.assertEqual(called, [("Mark", 1, 3)])

    def test_source_editor_annotation_masquerading_as_greek_is_not_accepted(self):
        result, called = resolved(document(greek="41N 1:3"))
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.shared_id)
        self.assertEqual(called, [])

    def test_editorial_or_cts_address_in_original_sbl_payload_must_not_map(self):
        for misleading in (
            "41N 1:3",
            " 41N 1:3 ",
            "urn:cts:copticLit:nt.mark.sahidica_ed:1.3",
            "",
        ):
            with self.subTest(payload=misleading):
                r, calls = resolved(document(greek=misleading))
                self.assertEqual(r.status, "ambiguous")
                self.assertEqual(calls, [])

    def test_wrong_cts_verse_or_missing_cts_is_not_enough(self):
        for doc in (document(vid_verse=4), document(include_vid=False)):
            with self.subTest(raw=doc.source_text[:120]):
                result, called = resolved(doc)
                self.assertEqual(result.status, "ambiguous")
                self.assertEqual(called, [])

    def test_generic_other_chapter_with_two_markers_not_whitelisted(self):
        d = document(chapter=10)
        d = replace(d, source_record_id="sahidica.mark/sahidica.mark:Mark_10")
        result, called = resolved(d)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(called, [])

    def test_generic_other_physical_record_not_whitelisted(self):
        d = replace(document(), source_record_id="sahidica.mark/sahidica.mark:Mark_02")
        result, called = resolved(d)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(called, [])

    def test_existing_editor_marker_does_not_use_the_no_editor_fallback(self):
        d = document(editor="41N 1:4")
        result, called = resolved(d)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(called, [])

    def test_attested_provenance_and_source_identity_still_required(self):
        cases = (
            document(provenance=False),
            replace(document(), metadata_duplicates={"chapter": ("1", "2")}),
            replace(document(), upstream_commit="forged"),
            replace(document(), corpus="unrelated"),
        )
        for d in cases:
            with self.subTest(record=d.source_record_id, pin=d.upstream_commit):
                if d.upstream_commit != PIN:
                    with self.assertRaisesRegex(ValueError, "revision"):
                        resolved(d)
                else:
                    result, called = resolved(d)
                    self.assertNotEqual(result.status, "reference_candidate")
                    self.assertEqual(called, [])

    def test_no_whole_coptic_word_scope_never_creates_ref(self):
        d = document()
        a = replace(d.sbl_annotations[0], word_ordinals=())
        result, called = resolved(replace(d, sbl_annotations=(a,)))
        self.assertEqual(result.status, "unresolved")
        self.assertEqual(called, [])

    def test_edition_unavailable_is_still_status_only(self):
        d = document(verse=3)
        result, called = resolved(d)
        self.assertEqual(result.target_book, "Mark")
        self.assertEqual(result.target_chapter, 1)


if __name__ == "__main__":
    unittest.main()
