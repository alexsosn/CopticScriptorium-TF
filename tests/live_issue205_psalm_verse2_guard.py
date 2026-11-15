"""Exact original-language *source verse2* vs Greek verse2 and later motif audit.

This test exposes false *same-number* Greek IDs, not a complete translation
alignment. The original TT and Greek text are read locally in CI and NEVER
written to the metadata-only report.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
import unicodedata
from unittest.mock import patch
from zipfile import ZipFile

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.lxx_module import verify_lxx_parent_feature_blobs
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from copticscriptorium_tf.lxx_psalm_guard import SOURCE_PIN, SOURCE_SHA, RULE_ID
from copticscriptorium_tf.parser import parse_tt_record

LXX_PIN = "f32a98eddf7eb239aa73ab863d70381e416d5076"
SOURCE_ZIP = Path("bohairic.ot/bohairic.ot_TT.zip")

# Short, public, edition-specific lexical contrasts, NOT token-to-token
# alignments. The alternate Greek verse is a cross-check, NOT a new mapping.
ANCHORS = {
    3: {
        "alternative": 3,
        "coptic_source2": ("ⲙⲏϣ", "ϫⲱ"),
        "greek_alternative": ("λεγουσιν", "ψυχη"),
        "greek_same_number_absent": ("λεγουσιν",),
    },
    17: {
        "alternative": 3,
        "coptic_source2": ("ⲧⲁϫⲣⲟ", "ⲡⲁⲙⲁⲙⲫⲱⲧ"),
        "greek_alternative": ("στερεωμα", "καταφυγη"),
        "greek_same_number_absent": ("στερεωμα",),
    },
    51: {
        "alternative": 4,
        "coptic_source2": ("ⲗⲁⲥ", "ⲁⲇⲓⲕⲓⲁ"),
        "greek_alternative": ("γλωσσα", "αδικιαν"),
        "greek_same_number_absent": ("γλωσσα",),
    },
}


def canonical(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("missing original source or Greek word form")
    nfd = unicodedata.normalize("NFD", value.casefold())
    return "".join(c for c in nfd if unicodedata.category(c).startswith("L"))


def run(coptic_root: Path, greek_tf: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("refusing to overwrite Psalm source evidence")
    verify_lxx_parent_feature_blobs(greek_tf)
    greek = Fabric(locations=[str(greek_tf)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    if (
        not greek or greek.F.otype.maxSlot != 623693
        or len(greek.F.otype.s("verse")) != 30371
    ):
        raise ValueError("Greek LXX parent native TF profile mismatched")
    greek_cache: dict[tuple[int, int], tuple[str, ...]] = {}

    def native_greek(chapter: int, verse: int) -> tuple[str, ...]:
        key = (chapter, verse)
        if key not in greek_cache:
            v = greek.T.nodeFromSection(("Ps", chapter, verse))
            if v is None or greek.F.otype.v(v) != "verse":
                raise ValueError("Greek native Psalm verse missing")
            ws = tuple(greek.L.d(v, otype="word"))
            if not ws or len(ws) != len(set(ws)) or ws != tuple(sorted(ws)):
                raise ValueError("Greek native Psalm word slots missing/duplicate/reordered")
            greek_cache[key] = tuple(canonical(greek.F.word.v(w)) for w in ws)
        return greek_cache[key]

    def lookup(book: str, chapter: int, verse: int) -> int | None:
        node = greek.T.nodeFromSection((book, chapter, verse))
        if node is not None and greek.F.otype.v(node) != "verse":
            raise ValueError("Greek numeric target has wrong native node type")
        return node

    records: list[dict[str, object]] = []
    with ZipFile(coptic_root / SOURCE_ZIP) as archive:
        members = {}
        for entry in archive.infolist():
            name = Path(entry.filename).name
            if name in members:
                raise ValueError("duplicate Coptic physical source basename")
            members[name] = entry
        for chapter in sorted(ANCHORS):
            name = f"19_Psalmi_{chapter:03d}.tt"
            entry = members.get(name)
            if entry is None or entry.is_dir():
                raise ValueError("missing exact Coptic Psalm physical TT")
            doc = parse_tt_record(
                archive.read(entry),
                source_record_id=f"bohairic.ot/bohairic.ot:19_Psalmi_{chapter:03d}",
                source_path=f"{SOURCE_ZIP}!{entry.filename}",
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit=SOURCE_PIN,
                packaging="archive",
            )
            if doc.source_sha256 != SOURCE_SHA[chapter]:
                raise ValueError("pinned original TT content SHA mismatch")
            original = tuple(w for w in doc.words if w.verse_n == "2")
            if not original:
                raise ValueError("original Coptic source verse2 has no words")
            coptic_forms = tuple(canonical(w.norm) for w in original)
            anchor = ANCHORS[chapter]
            exact = native_greek(chapter, 2)
            alternate = native_greek(chapter, anchor["alternative"])
            matches = {
                "coptic_source2_curated_words_attested": all(
                    canonical(w) in coptic_forms for w in anchor["coptic_source2"]
                ),
                "later_greek_curated_words_attested": all(
                    canonical(w) in alternate for w in anchor["greek_alternative"]
                ),
                "same_number_greek_lacks_discriminating_motifs": all(
                    canonical(w) not in exact
                    for w in anchor["greek_same_number_absent"]
                ),
            }
            if not all(matches.values()):
                raise ValueError(
                    f"original Psalm {chapter} word-level negative/positive "
                    f"controls failed: {matches}"
                )
            # Re-run the same real doc with only the specific source2 guard
            # bypassed to prove the pre-change resolver did return a wrong ID.
            with patch(
                "copticscriptorium_tf.lxx_reference.blocked_same_number_psalm_body",
                side_effect=lambda d, *, lxx_book, source_chapter, source_verse:
                    None if source_verse == 2 else
                    __import__(
                        "copticscriptorium_tf.lxx_psalm_guard",
                        fromlist=["blocked_same_number_psalm_body"]
                    ).blocked_same_number_psalm_body(
                        d, lxx_book=lxx_book,
                        source_chapter=source_chapter, source_verse=source_verse
                    ),
            ):
                baseline = [r for r in resolve_coptic_lxx_references(doc, lookup=lookup)
                            if r.source_verse_n == "2"]
            refs = resolve_coptic_lxx_references(doc, lookup=lookup)
            protected = [r for r in refs if r.source_verse_n == "2"]
            third = [r for r in refs if r.source_verse_n == "3"]
            if len(baseline) != 1 or len(protected) != 1:
                raise ValueError("source2 original TT does not form one reference group")
            b, now = baseline[0], protected[0]
            expected_wrong = f"CenterBLC/LXX:1935:Ps:{chapter}:2"
            if b.status != "reference_candidate" or b.shared_id != expected_wrong:
                raise ValueError("pre-change source2 false numeric candidate not demonstrated")
            if (
                now.status != "ambiguous" or now.shared_id is not None
                or now.lxx_node is not None or now.lxx_chapter is not None
                or now.lxx_verse is not None or RULE_ID not in now.evidence
                or now.source_verse_n != "2"
                or now.source_word_ordinals != b.source_word_ordinals
            ):
                raise ValueError("source2 false numeric ID not removed correctly")
            if len(third) != 1 or third[0].status != "reference_candidate":
                raise ValueError("source3 mapping unexpectedly shifted or blocked")
            records.append({
                "source_chapter": chapter,
                "source_record_id": doc.source_record_id,
                "original_tt_sha256": doc.source_sha256,
                "source2_word_slots": len(original),
                "source2_first_word_ordinal": original[0].ordinal,
                "source2_last_word_ordinal": original[-1].ordinal,
                "former_false_target": expected_wrong,
                "corrected_status": now.status,
                "corrected_has_greek_id": now.shared_id is not None,
                "source3_original_number_unmodified": third[0].source_verse_n == "3",
                "greek_comparison_reference_only": f"Ps {chapter}:{anchor['alternative']}",
                "greek_verse2_word_slots": len(exact),
                "greek_alternative_verse_word_slots": len(alternate),
                "source_language_motif_checks": matches,
            })
    if len(records) != 3:
        raise ValueError("not all three source documents audited")
    report = {
        "schema": "bohairic_three_psalms_second_body_false_id_audit_v1",
        "source_commit": SOURCE_PIN,
        "greek_commit": LXX_PIN,
        "rule_id": RULE_ID,
        "total_source2_words": sum(r["source2_word_slots"] for r in records),
        "false_numeric_groups_removed": len(records),
        "greek_verses_compared": len(greek_cache),
        "records": records,
        "interpretation": (
            "Exact source-native lexical motif comparisons and false same-number "
            "candidate removal; NO complete Coptic-to-Greek verse or word alignment"
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "total_source2_words": report["total_source2_words"],
        "false_numeric_groups_removed": len(records),
        "greek_verses_compared": len(greek_cache),
        "source_chapters": [r["source_chapter"] for r in records],
        "word_counts": [r["source2_word_slots"] for r in records],
        "all_anchor_checks_pass": all(
            all(row["source_language_motif_checks"].values()) for row in records
        ),
        "type": "numeric candidate negative controls, NOT positive verse alignment",
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: python tests/live_issue205_psalm_verse2_guard.py "
            "PINNED_COPTIC_ROOT PINNED_GREEK_TF OUTPUT_JSON"
        )
    run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
