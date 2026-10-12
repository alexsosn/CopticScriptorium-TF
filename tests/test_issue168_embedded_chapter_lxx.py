"""RED-first cross-chapter Coptic→LXX address ambiguity tests (#168).

The source <chapter_n> annotation has an exact position, but is NOT a
validated Septuagint chapter identity. Never assign a guessed Greek chapter.
"""
from __future__ import annotations

import unittest
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references

UPSTREAM = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def parse(chapter_markup: str):
    first = (
        '<meta corpus="sahidic.ruth" chapter="2">'
        '<verse_n verse_n="1">'
        '<norm_group norm_group="a">'
        '<norm xml:id="u1" new_sent="true" func="root" norm="a">a</norm>'
        '</norm_group>'
    )
    source = first + chapter_markup
    return parse_tt_record(
        source.encode("utf-8"),
        source_record_id="sahidic.ruth/sahidic.ruth:Ruth_02",
        source_path="sahidic.ruth/sahidic.ruth_TT/Ruth_02.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=UPSTREAM,
    )


def following(word: str = "b", *, verse: str = "1"):
    return (
        f'<verse_n verse_n="{verse}">'
        '<norm_group norm_group="b">'
        f'<norm xml:id="u2" new_sent="true" func="root" norm="{word}">{word}</norm>'
        '</norm_group>'
    )


class EmbeddedChapterLxxSafety(unittest.TestCase):
    def test_different_chapter_at_same_verse_number_preserves_prior_candidate(self):
        doc = parse(
            '<chapter_n chapter_n="3">'
            + following()
            + '</chapter_n>'
        )
        self.assertEqual(len(doc.reference_annotations), 1)
        self.assertEqual(doc.reference_annotations[0].kind, "chapter_n")
        self.assertEqual(doc.reference_annotations[0].start_after_word_ordinal, 1)
        calls = []
        refs = resolve_coptic_lxx_references(
            doc, lookup=lambda *k: calls.append(k) or 100,
        )
        self.assertEqual([r.source_word_ordinals for r in refs], [(1,), (2,)])
        self.assertEqual([r.status for r in refs], ["reference_candidate", "ambiguous"])
        self.assertEqual(calls, [("Ruth", 2, 1)])
        self.assertEqual(refs[0].shared_id, "CenterBLC/LXX:1935:Ruth:2:1")
        self.assertIsNone(refs[1].shared_id)
        self.assertIsNone(refs[1].lxx_node)
        self.assertIn("chapter", refs[1].reason)

    def test_same_numeric_chapter_marker_does_not_invent_crosswalk(self):
        doc = parse('<chapter_n chapter_n="02">' + following() + '</chapter_n>')
        refs = resolve_coptic_lxx_references(doc, lookup=lambda *k: 100)
        self.assertEqual([r.source_word_ordinals for r in refs], [(1,), (2,)])
        self.assertEqual([r.status for r in refs], ["reference_candidate"] * 2)
        self.assertEqual([r.shared_id for r in refs],
                         ["CenterBLC/LXX:1935:Ruth:2:1"] * 2)

    def test_invalid_embedded_chapter_blocks_only_after_boundary(self):
        doc = parse('<chapter_n chapter_n="III">' + following() + '</chapter_n>')
        called = []
        refs = resolve_coptic_lxx_references(doc, lookup=lambda *k: called.append(k) or 100)
        self.assertEqual([r.status for r in refs], ["reference_candidate", "ambiguous"])
        self.assertEqual(called, [("Ruth", 2, 1)])

    def test_intra_word_chapter_marker_does_not_map_unsplit_word(self):
        doc = parse(
            '<norm_group norm_group="b">'
            '<norm xml:id="u2" new_sent="true" func="root" norm="ab">'
            'a<chapter_n chapter_n="3">b</chapter_n>c</norm>'
            '</norm_group>'
        )
        called = []
        refs = resolve_coptic_lxx_references(doc, lookup=lambda *k: called.append(k) or 100)
        self.assertEqual([r.source_word_ordinals for r in refs], [(1,), (2,)])
        self.assertEqual([r.status for r in refs], ["reference_candidate", "ambiguous"])
        self.assertEqual(called, [("Ruth", 2, 1)])

    def test_marcion_chapter_annotation_cannot_override_biblical_chapter(self):
        doc = parse('<marcion_chapter_n marcion_chapter_n="9">' + following() + '</marcion_chapter_n>')
        self.assertEqual(doc.reference_annotations[0].kind, "marcion_chapter_n")
        refs = resolve_coptic_lxx_references(doc, lookup=lambda *k: 100)
        self.assertEqual([r.status for r in refs], ["reference_candidate"])
        self.assertEqual(refs[0].source_word_ordinals, (1, 2))

    def test_regular_unchanged_verse_markers_keep_prior_semantics(self):
        doc = parse(following(verse="2"))
        refs = resolve_coptic_lxx_references(doc, lookup=lambda b, c, v: 1000 + v)
        self.assertEqual([r.status for r in refs], ["reference_candidate"] * 2)
        self.assertEqual([r.lxx_verse for r in refs], [1, 2])


if __name__ == "__main__":
    unittest.main()
