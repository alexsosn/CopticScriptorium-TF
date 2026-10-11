"""RED-first tests: source verse-tag *occurrences* can differ from word-group keys."""
from __future__ import annotations

import json
import unittest

from copticscriptorium_tf.verse_marker_topology import VerseMarkerTopologyAudit
from copticscriptorium_tf.lxx_coverage import CopticLxxCoverageAudit
from copticscriptorium_tf.parser import parse_tt_record

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def doc(body: str, name: str = "test"):
    raw = '<meta chapter="2" corpus="sahidic.ruth">' + body
    return parse_tt_record(
        raw.encode("utf-8"),
        source_record_id=f"sahidic.ruth/sahidic.ruth:{name}",
        source_path=f"sahidic.ruth/sahidic.ruth_TT/{name}.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )


def token(n: int) -> str:
    return (
        f'<norm_group norm_group="w{n}">'
        f'<norm xml:id="u{n}" new_sent="true" func="root" norm="w{n}">'
        f'w{n}</norm></norm_group>'
    )


class VerseMarkerTopologyContractTests(unittest.TestCase):
    def test_real_scanner_counts_duplicate_gap_decrease_zero_word_and_missing_number(self):
        source = (
            '<meta chapter="2">'
            '<verse_n verse_n="1">' + token(1)
            + '<verse_n verse_n="1">' + token(2)
            + '<verse_n verse_n="3">'
            + '<verse_n verse_n="2">' + token(3)
            + '<verse_n verse_n="2">' + token(4)
            + '<verse_n verse_n="">' + token(5)
        )
        audit = VerseMarkerTopologyAudit()
        audit.add(source, "sahidic.ruth/sahidic.ruth:case")
        report = audit.report()
        self.assertEqual(report["source_records"], 1)
        self.assertEqual(report["opening_verse_n_tags"], 6)
        self.assertEqual(report["categories"], {
            "duplicate_same_number": 2,
            "nonmonotonic": 1,
            "gapped": 1,
            "zero_word_verse": 1,
            "missing_or_nonpositive_literal": 1,
        })
        self.assertEqual(report["examples"]["duplicate_same_number"], [
            "sahidic.ruth/sahidic.ruth:case"
        ])
        self.assertEqual(report["source_records_with_verse_n"], 1)
        self.assertNotIn("norm_group", json.dumps(report))

    def test_closing_tags_are_not_new_verse_occurrences(self):
        audit = VerseMarkerTopologyAudit()
        audit.add('<verse_n verse_n="1"><norm norm="a">x</norm></verse_n>', "q/q:a")
        self.assertEqual(audit.report()["opening_verse_n_tags"], 1)
        self.assertEqual(audit.report()["categories"], {})

    def test_source_identity_examples_bounded_and_order_independent(self):
        raw = '<verse_n verse_n="1"><verse_n verse_n="1">' + token(1)
        audit = VerseMarkerTopologyAudit()
        for name in ("z", "c", "a", "b", "a"):
            audit.add(raw, f"test/test:{name}")
        self.assertEqual(audit.report()["examples"]["duplicate_same_number"], [
            "test/test:a", "test/test:b", "test/test:c"
        ])
        self.assertEqual(audit.report()["categories"]["duplicate_same_number"], 5)

    def test_word_scoped_resolver_can_hide_duplicate_marker_event_but_audit_reports_it(self):
        raw = ('<verse_n verse_n="1">' + token(1)
               + '<verse_n verse_n="1">' + token(2))
        d = doc(raw)
        self.assertEqual([word.verse_n for word in d.words], ["1", "1"])
        audit = CopticLxxCoverageAudit(source_commit=PIN, lookup=lambda *_: 42)
        audit.add(d)
        report = audit.report()
        self.assertEqual(report["ot_reference_statuses"], {"reference_candidate": 1})
        self.assertEqual(report["marker_topology"]["categories"]["duplicate_same_number"], 1)
        self.assertEqual(report["marker_topology"]["opening_verse_n_tags"], 2)
        self.assertEqual(report["marker_topology"]["source_records"], 1)
        self.assertEqual(report["ot_word_statuses"], {"reference_candidate": 2})

    def test_nonbiblical_audited_without_promoting_to_greek(self):
        d = parse_tt_record(
            ('<meta>' + '<verse_n verse_n="1">' + token(1)).encode(),
            source_record_id="pachomius/pachomius:test",
            source_path="pachomius/pachomius_TT/test.tt",
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        called = []
        audit = CopticLxxCoverageAudit(source_commit=PIN, lookup=lambda *key: called.append(key) or 55)
        audit.add(d)
        self.assertEqual(audit.report()["marker_topology"]["opening_verse_n_tags"], 1)
        self.assertEqual(audit.report()["source_scopes"], {"undetermined": 1})
        self.assertEqual(called, [])


if __name__ == "__main__":
    unittest.main()
