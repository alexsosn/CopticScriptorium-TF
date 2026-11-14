"""RED-first: all physical Bohairic Psalm verse-zero TT spans (#199)."""
from __future__ import annotations

from dataclasses import replace
import json
import unittest

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.psalm_zero_boundary import PsalmZeroAudit, inspect_psalm_zero

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def make_doc(chapter=1, *, corpus="bohairic.ot", work="pss", edition="bohairic_ed",
             body=None, record=None, source_commit=COPTIC_PIN):
    chapter_text = f"{chapter:02d}"
    name = record or (
        f"19_Psalmi_{chapter:03d}" if work == "pss" else
        f"25_Lamentationes_{chapter_text}"
    )
    metadata = (
        f'<meta chapter="{chapter_text}" '
        f'document_cts_urn="urn:cts:copticLit:ot.{work}.{edition}:{chapter_text}">'
    )
    if body is None:
        body = '<verse_n verse_n="0"><verse_n verse_n="1">' + norm("a", 1)
    return parse_tt_record(
        (metadata + body).encode("utf-8"),
        source_record_id=f"{corpus}/{corpus}:{name}",
        source_path=f"{corpus}/{corpus}_TT.zip!{name}.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=source_commit,
        packaging="archive",
    )


def norm(text, n):
    return (
        f'<norm_group norm_group="g{n}"><norm xml:id="w{n}" '
        f'new_sent="true" func="root" norm="{text}">{text}</norm></norm_group>'
    )


class PsalmZeroSourceBoundaryTests(unittest.TestCase):

    def test_empty_zero_span_is_wordless_not_greek_verse_zero(self):
        d = make_doc()
        calls = []
        x = inspect_psalm_zero(d, greek_verse=lambda chapter, verse: calls.append(
            (chapter, verse)) or 501, greek_subverse=lambda node: ("a",))
        self.assertEqual(x["status"], "empty_zero_span")
        self.assertEqual(x["source_verse_literal"], "0")
        self.assertEqual(x["zero_span_word_count"], 0)
        self.assertEqual(x["next_source_verse_literal"], "1")
        self.assertEqual(x["greek_next_address"], "Ps 1:1")
        self.assertEqual(x["greek_next_status"], "present")
        self.assertEqual(x["greek_next_subverse_count"], 1)
        self.assertEqual(calls, [(1, 1)])
        self.assertNotIn("greek_zero_verse", x)

    def test_nonempty_zero_span_keeps_original_word_not_automapped(self):
        body = '<verse_n verse_n="0">' + norm("TITLE_SENTINEL", 1) + (
            '<verse_n verse_n="1">' + norm("body", 2)
        )
        d = make_doc(body=body)
        x = inspect_psalm_zero(d, greek_verse=lambda *_: 42)
        self.assertEqual(x["status"], "nonempty_zero_span")
        self.assertEqual(x["zero_span_word_count"], 1)
        self.assertEqual([w.verse_n for w in d.words], ["0", "1"])
        self.assertNotIn("TITLE_SENTINEL", json.dumps(x))
        self.assertEqual(x["greek_next_address"], "Ps 1:1")

    def test_missing_first_zero_and_out_of_order_or_duplicate_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "zero|first"):
            inspect_psalm_zero(make_doc(body='<verse_n verse_n="1">' + norm("x", 1)))
        with self.assertRaisesRegex(ValueError, "first|zero"):
            inspect_psalm_zero(make_doc(body=norm("x", 1) + '<verse_n verse_n="0">' + norm("y", 2)))
        with self.assertRaisesRegex(ValueError, "duplicate|multiple|zero"):
            inspect_psalm_zero(make_doc(body=(
                '<verse_n verse_n="0">' + norm("x", 1) +
                '<verse_n verse_n="0">' + norm("y", 2) +
                '<verse_n verse_n="1">' + norm("z", 3)
            )))

    def test_missing_or_invalid_next_boundary_stays_unresolved(self):
        x = inspect_psalm_zero(make_doc(body='<verse_n verse_n="0">' + norm("x", 1)))
        self.assertEqual(x["status"], "missing_next_boundary")
        self.assertEqual(x["greek_next_status"], "not_checked")
        x = inspect_psalm_zero(make_doc(body=(
            '<verse_n verse_n="0">' + norm("x", 1) +
            '<verse_n verse_n="zero">' + norm("y", 2)
        )))
        self.assertEqual(x["status"], "invalid_next_boundary")
        self.assertEqual(x["greek_next_status"], "not_checked")

    def test_other_works_and_dialects_not_classified_as_psalm(self):
        calls = []
        self.assertIsNone(inspect_psalm_zero(
            make_doc(work="lam", chapter=1), greek_verse=lambda *args: calls.append(args)
        ))
        self.assertIsNone(inspect_psalm_zero(
            make_doc(corpus="sahidic.ot", edition="coptot"), greek_verse=lambda *args: calls.append(args)
        ))
        self.assertEqual(calls, [])

    def test_corpus_revision_and_cts_must_be_exact(self):
        for mutation in (
            dict(source_commit="0" * 40),
            dict(record="other"),
            dict(edition="wrong_ed"),
            dict(chapter=0),
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaisesRegex(ValueError, "source|chapter|edition|record|revision"):
                    inspect_psalm_zero(make_doc(**mutation))

    def test_batch_partitions_and_bounded_examples_no_text(self):
        audit = PsalmZeroAudit()
        for chapter in (4, 3, 2, 1):
            item = make_doc(chapter=chapter)
            audit.add(item, inspect_psalm_zero(item, greek_verse=lambda *args: 77))
        report = audit.report()
        self.assertEqual(report["counts"], {"empty_zero_span": 4})
        self.assertEqual(report["source_records"], 4)
        self.assertEqual(len(report["records"]), 4)
        self.assertEqual(report["examples"], [
            "bohairic.ot/bohairic.ot:19_Psalmi_001",
            "bohairic.ot/bohairic.ot:19_Psalmi_002",
            "bohairic.ot/bohairic.ot:19_Psalmi_003",
        ])
        self.assertEqual([r["source_chapter"] for r in report["records"]], [1, 2, 3, 4])
        self.assertNotIn("<norm", json.dumps(report))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit.add(make_doc(chapter=1), inspect_psalm_zero(make_doc(chapter=1)))

    def test_missing_greek_target_is_visible_without_invented_mapping(self):
        x = inspect_psalm_zero(make_doc(chapter=151), greek_verse=lambda *_: None)
        self.assertEqual(x["greek_next_status"], "absent")
        self.assertEqual(x["greek_next_address"], "Ps 151:1")
        self.assertNotIn("greek_ref_id", x)


if __name__ == "__main__":
    unittest.main()
