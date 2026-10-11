"""RED-first invariants for exact source-byte-qualified OT gap context (#149)."""
from __future__ import annotations

from hashlib import sha256
import unittest

from copticscriptorium_tf.ot_variant_source_context import (
    SourceContextError,
    inspect_source_gap_context,
)


def source(body: str, *, note: str = "Theodotion edition may be mentioned"):
    raw = (
        f'<meta chapter="5" note="{note}" document_cts_urn="urn:cts:copticLit:ot.dan.coptot:5">'
        + body
    ).encode("utf-8")
    return raw, sha256(raw).hexdigest()


MARKUP = (
    '<verse_n verse_n="10">'
    '<norm_group norm_group="x"><norm xml:id="u1" new_sent="true" norm="a">a</norm>'
    '<norm xml:id="u2" norm="b">b</norm></norm_group>'
    '<verse_n verse_n="16">'
    '<norm_group norm_group="y"><norm xml:id="u3" new_sent="true" norm="c">c</norm></norm_group>'
)


class PinnedCopticGapSourceEvidenceTests(unittest.TestCase):
    def test_gap_has_two_real_preceding_coptic_words_not_six_fake_missing_verses(self):
        raw, sha = source(MARKUP)
        report = inspect_source_gap_context(
            raw, expected_sha256=sha, expected_chapter=5,
            expected_events=((2, 10, 16),),
        )
        self.assertEqual(len(report), 1)
        row = report[0]
        self.assertEqual(row.source_marker_ordinal, 2)
        self.assertEqual(row.words_since_prior_verse_marker, 2)
        self.assertEqual(row.missing_number_count, 5)
        self.assertEqual(row.editorial_greek_name_mentions, ("theodotion",))
        self.assertEqual(row.source_metadata_keys, ("chapter", "document_cts_urn", "note"))
        self.assertEqual(row.status, "source_context_only")

    def test_identical_source_span_without_edition_note_still_not_qualified(self):
        raw, sha = source(MARKUP, note="Unrelated source provenance")
        report = inspect_source_gap_context(
            raw, expected_sha256=sha, expected_chapter=5,
            expected_events=((2, 10, 16),),
        )
        self.assertEqual(report[0].editorial_greek_name_mentions, ())
        self.assertEqual(report[0].status, "source_context_only")

    def test_fail_closed_on_forged_source_and_event_position_or_numbers(self):
        raw, sha = source(MARKUP)
        cases = [
            (raw + b" ", sha, 5, ((2, 10, 16),)),
            (raw, "a" * 64, 5, ((2, 10, 16),)),
            (raw, sha, 6, ((2, 10, 16),)),
            (raw, sha, 5, ((1, 10, 16),)),
            (raw, sha, 5, ((2, 9, 16),)),
            (raw, sha, 5, ((2, 10, 17),)),
            (raw, sha, 5, ((2, 10, 16), (2, 10, 16))),
        ]
        for payload, digest, chap, expected in cases:
            with self.subTest(expected=expected, chapter=chap):
                with self.assertRaises(SourceContextError):
                    inspect_source_gap_context(
                        payload, expected_sha256=digest,
                        expected_chapter=chap, expected_events=expected,
                    )

    def test_chapter_boundary_cannot_masquerade_as_adjacent_numeric_gap(self):
        raw, sha = source(
            '<verse_n verse_n="10">'
            '<norm_group norm_group="x"><norm xml:id="u1" new_sent="true" norm="a">a</norm></norm_group>'
            '<chapter_n chapter_n="6">'
            '<verse_n verse_n="16">'
            '<norm_group norm_group="y"><norm xml:id="u2" new_sent="true" norm="b">b</norm></norm_group>'
        )
        with self.assertRaises(SourceContextError):
            inspect_source_gap_context(
                raw, expected_sha256=sha, expected_chapter=5,
                expected_events=((2, 10, 16),),
            )

    def test_bounded_source_metadata_only_never_contains_source_words(self):
        raw, sha = source(
            '<verse_n verse_n="10">'
            '<norm_group norm_group="SECRETWORD"><norm xml:id="u1" new_sent="true" norm="SECRETWORD">SECRETWORD</norm></norm_group>'
            '<verse_n verse_n="16">'
            '<norm_group norm_group="y"><norm xml:id="u2" new_sent="true" norm="b">b</norm></norm_group>'
        )
        report = inspect_source_gap_context(
            raw, expected_sha256=sha, expected_chapter=5,
            expected_events=((2, 10, 16),),
        )
        self.assertNotIn("SECRETWORD", repr(report))


if __name__ == "__main__":
    unittest.main()
