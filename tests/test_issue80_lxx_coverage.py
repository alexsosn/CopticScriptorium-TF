"""RED: complete-scope streaming Coptic OT→LXX candidate coverage matrix (#80)."""
from __future__ import annotations

import json
import unittest

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_coverage import CopticLxxCoverageAudit

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def make_doc(family, name, *, cts="", chapter="1", body="", book=""):
    meta = f' chapter="{chapter}"'
    if cts:
        meta += f' document_cts_urn="{cts}"'
    if book:
        meta += f' book="{book}"'
    raw = f"<meta{meta}>" + (body or (
        '<verse_n verse_n="1">'
        '<norm_group norm_group="x"><norm xml:id="u1" new_sent="true" '
        'func="root" norm="a">a</norm></norm_group>'
    ))
    return parse_tt_record(
        raw.encode("utf-8"),
        source_record_id=f"{family}/{family}:{name}",
        source_path=f"{family}/{family}_TT/{name}.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )


class FullCorpusCoverageAuditTests(unittest.TestCase):
    def test_partition_does_not_call_greek_for_nt_or_unknown(self):
        lookup_calls = []

        def lookup(b, c, v):
            lookup_calls.append((b, c, v))
            return 42 if (b, c, v) == ("Ruth", 2, 1) else None

        verses = (
            '<verse_n verse_n="1">'
            '<norm_group norm_group="a"><norm xml:id="u1" new_sent="true" func="root" norm="a">a</norm></norm_group>'
            '<verse_n verse_n="2">'
            '<norm_group norm_group="b"><norm xml:id="u2" new_sent="true" func="root" norm="b">b</norm></norm_group>'
        )
        records = [
            make_doc("sahidic.ruth", "ot1", chapter="2", body=verses),
            make_doc("sahidica.nt", "nt1", cts="urn:cts:copticLit:nt.mark.ed:1"),
            make_doc("pachomius-instructions", "unknown"),
        ]
        audit = CopticLxxCoverageAudit(source_commit=PIN, lookup=lookup)
        for record in records:
            audit.add(record)
        got = audit.report()
        self.assertEqual(got["totals"]["source_records"], 3)
        self.assertEqual(got["source_scopes"], {
            "nt_candidate": 1, "ot_candidate": 1, "undetermined": 1
        })
        self.assertEqual(got["totals"]["ot_candidate_word_slots"], 2)
        self.assertEqual(got["ot_reference_statuses"], {
            "reference_candidate": 1, "unresolved": 1
        })
        self.assertEqual(got["ot_word_statuses"], {
            "reference_candidate": 1, "unresolved": 1
        })
        self.assertEqual(lookup_calls, [("Ruth", 2, 1), ("Ruth", 2, 2)])
        self.assertEqual(got["totals"]["verse_position_events"], 0)

    def test_ambiguous_and_missing_work_fail_closed(self):
        seen = []
        audit = CopticLxxCoverageAudit(
            source_commit=PIN, lookup=lambda *key: seen.append(key) or 99
        )
        audit.add(make_doc("bohairic.ot", "gen", cts="urn:cts:copticLit:ot.gen.ed:1"))
        audit.add(make_doc("sahidic.ruth", "conflict", chapter="2", book="Jonah"))
        audit.add(make_doc("bohairic.ot", "unknown_work", cts="urn:cts:copticLit:ot.tob.ed:1"))
        out = audit.report()
        self.assertEqual(out["totals"]["source_records"], 3)
        self.assertEqual(out["ot_reference_statuses"], {
            "reference_candidate": 1, "ambiguous": 1, "unclassified_corpus": 1
        })
        self.assertEqual(seen, [("Gen", 1, 1)])
        self.assertEqual(out["totals"]["ot_candidate_word_slots"], 3)
        self.assertEqual(sum(out["ot_word_statuses"].values()), 3)

    def test_distinct_greek_verse_addresses_are_not_multiplied_by_witnesses(self):
        audit = CopticLxxCoverageAudit(source_commit=PIN, lookup=lambda *args: 81)
        audit.add(make_doc("sahidic.ruth", "one"))
        audit.add(make_doc("sahidic.ruth", "two"))
        summary = audit.report()
        self.assertEqual(summary["ot_reference_statuses"]["reference_candidate"], 2)
        self.assertEqual(summary["totals"]["distinct_candidate_lxx_verses"], 1)
        self.assertEqual(
            summary["candidate_lxx_books"]["Ruth"]["distinct_candidate_verses"], 1
        )

    def test_source_duplicate_or_wrong_revision_rejected(self):
        d = make_doc("sahidic.ruth", "r")
        audit = CopticLxxCoverageAudit(source_commit=PIN, lookup=lambda *args: 1)
        audit.add(d)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit.add(d)
        # Mirror the converter's case-folded physical identity collision gate.
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit.add(make_doc("sahidic.ruth", "R"))
        bad = make_doc("sahidic.ruth", "other")
        from dataclasses import replace
        with self.assertRaisesRegex(ValueError, "source revision"):
            audit.add(replace(bad, upstream_commit="wrong"))

    def test_midword_events_undetermined_word_and_bounded_deterministic_examples(self):
        audit = CopticLxxCoverageAudit(source_commit=PIN, lookup=lambda *args: 17)
        body = (
            '<verse_n verse_n="1">'
            '<norm_group norm_group="x">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="abc">'
            'SECRET_SENSITIVE_SOURCE_PAYLOAD<verse_n verse_n="2">c</norm>'
            '</norm_group>'
        )
        for n in ("z", "b", "a", "c"):
            audit.add(make_doc("sahidic.ruth", n, chapter="2", body=body))
        report = audit.report()
        self.assertEqual(report["totals"]["verse_position_events"], 4)
        self.assertEqual(report["ot_reference_statuses"], {"unresolved": 4})
        self.assertEqual(report["ot_word_statuses"], {"unresolved": 4})
        self.assertEqual(report["families"]["sahidic.ruth"]["examples"], [
            "sahidic.ruth/sahidic.ruth:a",
            "sahidic.ruth/sahidic.ruth:b",
            "sahidic.ruth/sahidic.ruth:c",
        ])
        self.assertNotIn("SECRET_SENSITIVE_SOURCE_PAYLOAD", json.dumps(report))
        self.assertEqual(report["schema"], "coptic_lxx_reference_coverage_v1")


if __name__ == "__main__":
    unittest.main()
