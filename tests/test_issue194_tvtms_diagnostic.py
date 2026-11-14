"""RED-first external versification diagnostic contracts (#194)."""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace

from copticscriptorium_tf.tvtms_diagnostic import (
    TvtmsDiagnostic, load_pinned_tvtms, TVTMS_GIT_BLOB_SHA,
)
from copticscriptorium_tf.lxx_versification import (
    BOHAIRIC_ZECH_CHAPTER_SHA, COPTIC_SOURCE_GIT,
    BOHAIRIC_ZECH_CROSSWALK_VERSION, propose_bohairic_zechariah,
)


def doc(*, corpus="bohairic.ot", chapter=1, sha=None, cts=None):
    return SimpleNamespace(
        corpus=corpus,
        dataset=corpus,
        source_record_id=(
            f"bohairic.ot/bohairic.ot:38_Zacharias_{chapter:02d}"
            if corpus == "bohairic.ot" else f"{corpus}/{corpus}:sample"
        ),
        source_sha256=sha or BOHAIRIC_ZECH_CHAPTER_SHA.get(chapter, "unverified"),
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=COPTIC_SOURCE_GIT,
        metadata={
            "document_cts_urn": cts or (
                f"urn:cts:copticLit:ot.zach.bohairic_ed:{chapter:02d}"
                if corpus == "bohairic.ot" else "urn:cts:copticLit:ot.jonah.coptot_ed:2"
            ),
            "chapter": str(chapter),
        },
    )


def ref(verse, *, chapter=2, lxx_verse=None, book="Zech", status="versification_candidate"):
    return SimpleNamespace(
        status=status,
        source_verse_n=str(verse),
        source_record_id=(
            f"bohairic.ot/bohairic.ot:38_Zacharias_{1 if verse >= 18 else 2:02d}"
            if book == "Zech" else "<synthetic_source>"
        ),
        source_word_ordinals=(verse,),
        lxx_book=book,
        lxx_chapter=chapter,
        lxx_verse=lxx_verse if lxx_verse is not None else verse,
        shared_id=(
            f"CenterBLC/LXX:1935:{book}:{chapter}:"
            f"{lxx_verse if lxx_verse is not None else verse}"
        ) if status in {"reference_candidate", "versification_candidate"} else None,
        evidence="source exact " + BOHAIRIC_ZECH_CROSSWALK_VERSION,
    )


class ExternalVersificationDiagnosticsTests(unittest.TestCase):
    def _mapping(self):
        return {
            "English->LXX": {
                **{f"Zechariah 1:{v}": {"chapter": 2, "verse": v - 17} for v in range(18, 22)},
                **{f"Zechariah 2:{v}": {"chapter": 2, "verse": v + 4} for v in range(1, 14)},
                "Jonah 2:1": {"chapter": 2, "verse": 2},
                "Exodus 25:6": None,
                "Genesis 5:32": {"chapter": 6, "verse": 1, "part": ".1"},
            },
        }

    def test_reviewed_rules_match_external_entries_on_all_seventeen_verses(self):
        audit = TvtmsDiagnostic(self._mapping())
        for chapter, verses in [(1, range(18, 22)), (2, range(1, 14))]:
            source = doc(chapter=chapter)
            pairs = []
            for v in verses:
                got = propose_bohairic_zechariah(
                    source, lxx_book="Zech", source_chapter=chapter, source_verse=v
                )
                self.assertIsNone(got.blocked_reason)
                pairs.append(ref(v, chapter=2, lxx_verse=got.lxx_verse))
            audit.add(source, pairs)
        report = audit.report()
        self.assertEqual(report["status_counts"], {"reviewed_agree": 17})
        self.assertEqual(report["reference_groups"], 17)
        self.assertEqual(report["by_book"]["Zech"]["reviewed_agree"], 17)
        self.assertEqual(sum(report["status_counts"].values()), 17)\n        self.assertNotEqual(\n            report["original_tvtms_sha256"],\n            report["derived_source_declared_sha256"],\n        )\n        self.assertIn("NOT independently reproducible", report["provenance_warning"])

    def test_one_wrong_reviewed_target_is_detected_not_silently_repaired(self):
        audit = TvtmsDiagnostic(self._mapping())
        audit.add(doc(chapter=1), [ref(18, chapter=2, lxx_verse=2)])
        report = audit.report()
        self.assertEqual(report["status_counts"], {"reviewed_disagree": 1})

    def test_cross_document_reference_cannot_fake_independent_zechariah_agreement(self):
        audit = TvtmsDiagnostic(self._mapping())
        forged = replace_ref(
            ref(18, chapter=2, lxx_verse=1),
            source_record_id="bohairic.ot/bohairic.ot:other",
        )
        audit.add(doc(chapter=1), [forged])
        self.assertEqual(audit.report()["status_counts"], {
            "source_scheme_unverified": 1
        })

    def test_jonah_english_offset_cannot_overwrite_lxx_style_coptic(self):
        audit = TvtmsDiagnostic(self._mapping())
        audit.add(doc(corpus="sahidic.jonah", chapter=2), [
            ref(1, book="Jonah", chapter=2, status="reference_candidate")
        ])
        self.assertEqual(audit.report()["status_counts"], {
            "source_scheme_unverified": 1
        })

    def test_wrong_source_sha_or_edition_never_qualifies_as_reviewed(self):
        audit = TvtmsDiagnostic(self._mapping())
        audit.add(doc(chapter=1, sha="forged"), [ref(18, chapter=2, lxx_verse=1)])
        audit.add(doc(chapter=1, cts="urn:cts:copticLit:ot.zach.other_ed:01"), [
            ref(18, chapter=2, lxx_verse=1)
        ])
        self.assertEqual(audit.report()["status_counts"], {
            "source_scheme_unverified": 2
        })

    def test_null_partial_missing_and_invalid_verses_fail_closed(self):
        audit = TvtmsDiagnostic(self._mapping())
        audit.add(doc(corpus="sahidic.ot", chapter=25), [
            ref(6, book="Exod", chapter=25, status="reference_candidate"),
        ])
        audit.add(doc(corpus="sahidic.ot", chapter=5), [
            ref(32, book="Gen", chapter=6, status="reference_candidate"),
        ])
        audit.add(doc(corpus="sahidic.ot", chapter=3), [
            replace_ref(ref(1, book="Ps", chapter=3, status="reference_candidate"), source_verse_n="0"),
            ref(1, book="Dan", chapter=1, status="unclassified_corpus"),
        ])
        audit.add(doc(corpus="sahidic.ot", chapter=2), [
            ref(1, book="Ruth", chapter=2, status="reference_candidate"),
        ])
        out = audit.report()
        self.assertEqual(out["status_counts"], {
            "external_non_1to1": 2,
            "no_explicit_exception": 1,
            "unclassifiable": 2,
        })

    def test_real_streaming_audit_excludes_nt_and_preserves_reference_partition(self):
        from copticscriptorium_tf.lxx_coverage import CopticLxxCoverageAudit
        from tests.test_issue80_lxx_coverage import PIN, make_doc
        external = TvtmsDiagnostic(self._mapping())
        audit = CopticLxxCoverageAudit(
            source_commit=PIN, lookup=lambda *address: 42,
            tvtms_diagnostic=external,
        )
        audit.add(make_doc("sahidic.ruth", "ruth", chapter="2"))
        audit.add(make_doc(
            "sahidica.nt", "mark", cts="urn:cts:copticLit:nt.mark.ed:1"
        ))
        audit.add(make_doc("pachomius-instructions", "unknown"))
        report = audit.report()
        diagnostic = report["external_tvtms_diagnostic"]
        self.assertEqual(report["totals"]["source_records"], 3)
        self.assertEqual(report["source_scopes"]["ot_candidate"], 1)
        self.assertEqual(diagnostic["reference_groups"], report["totals"]["ot_reference_groups"])
        self.assertEqual(diagnostic["word_slots"], report["totals"]["ot_candidate_word_slots"])
        self.assertEqual(diagnostic["status_counts"], {"no_explicit_exception": 1})

    def test_loader_rejects_altered_or_unpinned_data_before_parsing(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "mapping.json"
            p.write_text(json.dumps(self._mapping()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Git blob|checksum|pin"):
                load_pinned_tvtms(p)
            self.assertEqual(len(TVTMS_GIT_BLOB_SHA), 40)
            # Exact file name is not sufficient; bytes are required.

    def test_report_is_aggregate_only_and_examples_bounded(self):
        audit = TvtmsDiagnostic(self._mapping())
        for n in ("d", "c", "b", "a"):
            item = doc(chapter=1)
            item.source_record_id = f"bohairic.ot/bohairic.ot:{n}"
            item.source_text = "UNIQUE_SOURCE_CONTENT_NEVER_SERIALIZE"
            audit.add(item, [ref(18, chapter=2, lxx_verse=1)])
        report = audit.report()
        self.assertEqual(report["status_counts"], {"source_scheme_unverified": 4})
        self.assertEqual(report["by_family"]["bohairic.ot"]["examples"], [
            "bohairic.ot/bohairic.ot:a",
            "bohairic.ot/bohairic.ot:b",
            "bohairic.ot/bohairic.ot:c",
        ])
        self.assertNotIn("UNIQUE_SOURCE_CONTENT_NEVER_SERIALIZE", json.dumps(report))


def replace_ref(old, **changes):
    fields = vars(old).copy()
    fields.update(changes)
    return SimpleNamespace(**fields)


if __name__ == "__main__":
    unittest.main()
