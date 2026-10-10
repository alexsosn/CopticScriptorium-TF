"""RED-first Coptic OT → pinned LXX *reference candidate* contract (#70).

No Greek lexical equivalence is inferred merely because a book/chapter/verse
address exists in both textual traditions.
"""
from __future__ import annotations

from dataclasses import replace
import unittest

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references

SOURCE_REV = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def doc(raw: str, *, corpus: str, record: str):
    return parse_tt_record(
        raw.encode("utf-8"),
        source_record_id=f"{corpus}/{corpus}:{record}",
        source_path=f"{corpus}/{corpus}_TT/{record}.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=SOURCE_REV,
    )


def words(verses: list[tuple[str, str | None, str | None]]):
    out = []
    for i, (num, cts, label) in enumerate(verses, 1):
        out.append(f'<verse_n verse_n="{num}">')
        if cts:
            out.append(f'<vid_n vid_n="{cts}">')
        if label:
            out.append(f'<verse_vid verse_vid="{label}">')
        out.append(
            f'<norm_group norm_group="{i}"><norm xml:id="u{i}" '
            f'new_sent="true" func="root" norm="w{i}">w{i}</norm></norm_group>'
        )
    return "".join(out)


class CopticLxxReferenceResolverTests(unittest.TestCase):
    def test_sahidic_ruth_uses_full_verse_and_cts_evidence(self):
        d = doc(
            '<meta chapter="2" corpus="sahidic.ruth">'
            + words([
                ("1", "urn:cts:copticLit:ot.ruth.copto_edt:2.1", "Ruth 2:1"),
                ("2", "urn:cts:copticLit:ot.ruth.coptot_ed:2.2", "Ruth 2:2"),
            ]),
            corpus="sahidic.ruth", record="Ruth_02",
        )
        target = {("Ruth", 2, 1): 10001, ("Ruth", 2, 2): 10002}
        got = resolve_coptic_lxx_references(d, lookup=lambda *key: target.get(key))
        self.assertEqual([x.status for x in got], ["reference_candidate"] * 2)
        self.assertEqual([x.lxx_node for x in got], [10001, 10002])
        self.assertEqual(got[0].shared_id, "CenterBLC/LXX:1935:Ruth:2:1")
        self.assertEqual(got[0].source_word_ordinals, (1,))
        self.assertEqual(got[1].source_verse_vid, "Ruth 2:2")
        self.assertEqual(got[0].source_record_id, d.source_record_id)

    def test_verse_only_jonah_is_candidate_not_word_alignment(self):
        d = doc(
            '<meta chapter="2" corpus="sahidic.jonah">'
            + words([("1", None, None), ("2", None, None)]),
            corpus="sahidic.jonah", record="Jonah_02",
        )
        got = resolve_coptic_lxx_references(d, lookup=lambda b, c, v: 123 if v == 1 else None)
        self.assertEqual(got[0].status, "reference_candidate")
        self.assertEqual(got[0].evidence, "verse_n")
        self.assertEqual(got[0].lxx_book, "Jonah")
        self.assertEqual(got[1].status, "unresolved")
        self.assertIsNone(got[1].lxx_node)

    def test_bohairic_habakkuk_uses_lxx_book_abbreviation(self):
        d = doc(
            '<meta book="Habakkuk" chapter="02" corpus="bohairic.habakkuk">'
            + words([("1", None, None)]),
            corpus="bohairic.habakkuk", record="Habakkuk_02",
        )
        got = resolve_coptic_lxx_references(d, lookup=lambda b, c, v: 77 if (b,c,v)==("Hab",2,1) else None)
        self.assertEqual(got[0].lxx_book, "Hab")
        self.assertEqual(got[0].status, "reference_candidate")

    def test_multiword_verse_preserves_complete_span(self):
        d = doc(
            '<meta chapter="2">' + words([("1", None, None)])
            + '<norm_group norm_group="extra"><norm xml:id="u2" new_sent="true" func="root" norm="x">x</norm></norm_group>',
            corpus="sahidic.ruth", record="Ruth_02",
        )
        got = resolve_coptic_lxx_references(d, lookup=lambda *key: 3)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].source_word_ordinals, (1, 2))

    def test_conflicting_verse_vid_and_cts_fail_closed_without_lookup(self):
        raw = '<meta chapter="2">' + words([
            ("1", "urn:cts:copticLit:ot.ruth.coptot_ed:2.3", "Ruth 2:2")
        ])
        d = doc(raw, corpus="sahidic.ruth", record="Ruth_02")
        called = []
        got = resolve_coptic_lxx_references(
            d, lookup=lambda *key: called.append(key) or 123
        )
        self.assertEqual(got[0].status, "ambiguous")
        self.assertIsNone(got[0].lxx_node)
        self.assertEqual(called, [])

    def test_foreign_book_cts_with_same_numeric_verse_is_ambiguous(self):
        d = doc(
            '<meta chapter="2">'
            + words([("1", "urn:cts:copticLit:ot.jonah.coptot_ed:2.1", "Ruth 2:1")]),
            corpus="sahidic.ruth", record="Ruth_02",
        )
        called = []
        report = resolve_coptic_lxx_references(
            d, lookup=lambda *key: called.append(key) or 123
        )
        self.assertEqual(report[0].status, "ambiguous")
        self.assertIsNone(report[0].lxx_node)
        self.assertEqual(called, [])

    def test_forged_cts_work_substring_does_not_pass_exact_work_validation(self):
        # An attacker or corrupted source can contain the substring
        # 'ot.ruth.' without actually identifying the OT Ruth CTS work.
        raw = '<meta chapter="2">' + words([
            ("1", "urn:cts:unrelated:forged.ot.ruth.lookalike:2.1", "Ruth 2:1")
        ])
        d = doc(raw, corpus="sahidic.ruth", record="Ruth_02")
        called = []
        report = resolve_coptic_lxx_references(
            d, lookup=lambda *key: called.append(key) or 123
        )
        self.assertEqual(report[0].status, "ambiguous")
        self.assertIsNone(report[0].shared_id)
        self.assertFalse(called)

    def test_unsupported_ot_source_is_not_misclassified_nonbiblical(self):
        d = doc(
            '<meta chapter="2">' + words([("1", None, None)]),
            corpus="sahidic.ot", record="Jonah_02",
        )
        result = resolve_coptic_lxx_references(d, lookup=lambda *key: 3)
        self.assertEqual(result[0].status, "unclassified_corpus")
        self.assertIsNone(result[0].lxx_node)

    def test_dataset_conflict_and_unclassified_source_never_lookup(self):
        d = doc(
            '<meta book="Jonah" chapter="2">' + words([("1", None, None)]),
            corpus="sahidic.ruth", record="Ruth_02",
        )
        called = []
        got = resolve_coptic_lxx_references(d, lookup=lambda *key: called.append(key) or 1)
        self.assertEqual(got[0].status, "ambiguous")
        self.assertEqual(called, [])
        x = doc(
            '<meta chapter="2">' + words([("1", None, None)]),
            corpus="pachomius-instructions", record="x",
        )
        excluded = resolve_coptic_lxx_references(x, lookup=lambda *key: called.append(key) or 1)
        self.assertEqual(excluded[0].status, "unclassified_corpus")
        self.assertEqual(called, [])


if __name__ == "__main__":
    unittest.main()
