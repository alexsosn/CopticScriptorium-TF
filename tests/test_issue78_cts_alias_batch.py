"""RED-first real-work-evidence contracts for bulk Coptic OT→LXX candidate addresses."""
from __future__ import annotations

import unittest
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references


def make_doc(
    family: str,
    work: str | None,
    *,
    chapter: str = "1",
    verse: str = "1",
    book: str | None = None,
    marker_work: str | None = None,
    label: str | None = None,
):
    meta = f'chapter="{chapter}"'
    if work is not None:
        meta += f' document_cts_urn="urn:cts:copticLit:ot.{work}.edition:{chapter}"'
    if book is not None:
        meta += f' book="{book}"'
    markers = f'<verse_n verse_n="{verse}">'
    if marker_work is not None:
        markers += f'<vid_n vid_n="urn:cts:copticLit:ot.{marker_work}.edition:{chapter}.{verse}">'
    if label is not None:
        markers += f'<verse_vid verse_vid="{label}">'
    raw = (
        f"<meta {meta}>" + markers
        + '<norm_group norm_group="x">'
        + '<norm xml:id="u1" new_sent="true" func="root" norm="w">w</norm>'
        + '</norm_group>'
    )
    return parse_tt_record(
        raw.encode("utf-8"),
        source_record_id=f"{family}/{family}:r",
        source_path=f"{family}/{family}_TT/r.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit="3ac067f1709a0012daf39ea8da2fac79980176a5",
    )


class AuditedOtAliasBatchTests(unittest.TestCase):
    def _resolve(self, doc, *, expected):
        calls = []
        got = resolve_coptic_lxx_references(
            doc, lookup=lambda *key: calls.append(key) or 628821
        )
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].status, expected)
        return got[0], calls

    def test_actual_archived_genesis_cts_can_resolve_without_meta_book(self):
        record = make_doc(
            "bohairic.ot", "gen", marker_work="gen", label="Genesis 1:1"
        )
        hit, calls = self._resolve(record, expected="reference_candidate")
        self.assertEqual(calls, [("Gen", 1, 1)])
        self.assertEqual(hit.shared_id, "CenterBLC/LXX:1935:Gen:1:1")

    def test_batch_source_aliases_cover_real_work_shapes(self):
        rows = [
            ("sahidic.ot", "pss", "Ps"),
            ("sahidic.ot", "eccl", "Qoh"),
            ("sahidic.ot", "song", "Cant"),
            ("bohairic.ot", "zach", "Zech"),
            ("sahidic.ot", "zech", "Zech"),
            ("bohairic-jonah", "Jonah", "Jonah"),
            ("coptic-treebank", "jonah", "Jonah"),
            ("bohairic-treebank", "hab", "Hab"),
            ("sahidic.ot", "2macc", "2Mac"),
            ("sahidic.ot", "1sam", "1Sam"),
        ]
        for family, work, greek in rows:
            with self.subTest(family=family, work=work):
                hit, calls = self._resolve(
                    make_doc(family, work, marker_work=work),
                    expected="reference_candidate",
                )
                self.assertEqual(calls, [(greek, 1, 1)])
                self.assertEqual(hit.lxx_book, greek)

    def test_edition_ambiguous_work_not_guessed(self):
        for work in ("tob", "dan", "sus", "bel", "prman"):
            with self.subTest(work=work):
                hit, calls = self._resolve(
                    make_doc("sahidic.ot", work, marker_work=work),
                    expected="unclassified_corpus",
                )
                self.assertEqual(calls, [])
                self.assertIsNone(hit.shared_id)

    def test_document_cts_missing_in_multiwork_family_not_guessed(self):
        hit, calls = self._resolve(
            make_doc("sahidic.ot", None, book="Genesis"),
            expected="unclassified_corpus",
        )
        self.assertEqual(calls, [])
        self.assertIsNone(hit.shared_id)

    def test_conflicting_work_and_marker_not_mapped(self):
        hit, calls = self._resolve(
            make_doc("bohairic.ot", "gen", marker_work="exod"),
            expected="ambiguous",
        )
        self.assertEqual(calls, [])
        hit, calls = self._resolve(
            make_doc("sahidic.ruth", "gen", marker_work="gen"),
            expected="ambiguous",
        )
        self.assertEqual(calls, [])

    def test_nt_family_cannot_forge_ot_work_by_cts(self):
        hit, calls = self._resolve(
            make_doc("sahidica.nt", "gen", marker_work="gen"),
            expected="unclassified_corpus",
        )
        self.assertEqual(calls, [])

    def test_source_book_literal_disagreement_fails_closed(self):
        hit, calls = self._resolve(
            make_doc("bohairic.ot", "gen", book="Exodus", marker_work="gen"),
            expected="ambiguous",
        )
        self.assertEqual(calls, [])

    def test_existing_ruth_fallback_without_cts_retained(self):
        hit, calls = self._resolve(
            make_doc("sahidic.ruth", None, marker_work=None),
            expected="reference_candidate",
        )
        self.assertEqual(calls, [("Ruth", 1, 1)])


if __name__ == "__main__":
    unittest.main()
