"""Real pinned Coptic Psalm 3/17/51 verse1 false numeric ID guard (#203)."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
from zipfile import ZipFile

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from copticscriptorium_tf.lxx_module import verify_lxx_parent_feature_blobs
from copticscriptorium_tf.lxx_psalm_guard import (
    RULE_ID, SOURCE_SHA, SOURCE_PIN,
)
from copticscriptorium_tf.psalm_boundary_crosscheck import (
    SELECTED_SOURCE_SHA, LXX_PIN,
)

SOURCE_ZIP = Path("bohairic.ot/bohairic.ot_TT.zip")
SOURCE_ONE_WORDS = {1: 28, 3: 41, 17: 31, 51: 28, 149: 20, 151: 26}


def run(coptic_root: Path, greek_root: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("refusing to overwrite real Psalm mapping guard report")
    verify_lxx_parent_feature_blobs(greek_root)
    greek = Fabric(locations=[str(greek_root)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    if greek.F.otype.maxSlot != 623693 or len(greek.F.otype.s("verse")) != 30371:
        raise ValueError("pinned native LXX verse parent does not match")

    def lookup(book: str, chapter: int, verse: int) -> int | None:
        node = greek.T.nodeFromSection((book, chapter, verse))
        if node is not None and greek.F.otype.v(node) != "verse":
            raise ValueError("LXX target returned wrong parent node type")
        return node

    cases: list[dict[str, object]] = []
    with ZipFile(coptic_root / SOURCE_ZIP) as archive:
        members = {}
        for obj in archive.infolist():
            basename = Path(obj.filename).name
            if basename in members:
                raise ValueError("duplicate physical original Coptic TT archive name")
            members[basename] = obj
        for chapter in sorted(SELECTED_SOURCE_SHA):
            basename = f"19_Psalmi_{chapter:03d}.tt"
            if basename not in members:
                raise ValueError("missing original source Psalm physical record")
            obj = members[basename]
            doc = parse_tt_record(
                archive.read(obj),
                source_record_id=f"bohairic.ot/bohairic.ot:19_Psalmi_{chapter:03d}",
                source_path=f"{SOURCE_ZIP}!{obj.filename}",
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit=SOURCE_PIN,
                packaging="archive",
            )
            if doc.source_sha256 != SELECTED_SOURCE_SHA[chapter]:
                raise ValueError("source TT SHA256 mismatched pinned control")
            before = tuple(w for w in doc.words if w.verse_n == "1")
            if len(before) != SOURCE_ONE_WORDS[chapter]:
                raise ValueError("Coptic first body verse native word count changed")
            if lookup("Ps", chapter, 1) is None:
                raise ValueError("Greek Psalm verse1 numeric false-positive control absent")
            rows = [r for r in resolve_coptic_lxx_references(doc, lookup=lookup)
                    if r.source_verse_n == "1"]
            if len(rows) != 1:
                raise ValueError("source Psalm verse1 does not have exactly one group")
            ref = rows[0]
            blocked = chapter in SOURCE_SHA
            if blocked:
                if (
                    ref.status != "ambiguous"
                    or ref.shared_id is not None
                    or ref.lxx_node is not None
                    or ref.lxx_chapter is not None
                    or ref.lxx_verse is not None
                    or RULE_ID not in ref.evidence
                    or not ref.reason.startswith(RULE_ID)
                ):
                    raise ValueError("known false same-number Psalm1 Coptic/LXX group NOT blocked")
                # Tampering a byte pin MUST NOT give source verse1 a Greek title.
                forged = replace(doc, source_sha256="0" * 64)
                bad = [r for r in resolve_coptic_lxx_references(forged, lookup=lookup)
                       if r.source_verse_n == "1"]
                if len(bad) != 1 or bad[0].status != "ambiguous" or (
                    bad[0].shared_id is not None
                ):
                    raise ValueError("forged source SHA silently restored Greek title candidate")
            else:
                if ref.status != "reference_candidate" or (
                    ref.shared_id != f"CenterBLC/LXX:1935:Ps:{chapter}:1"
                ):
                    raise ValueError("unaffected Bohairic Psalm1 candidate changed")
            cases.append({
                "chapter": chapter,
                "original_source_sha256": doc.source_sha256,
                "source_verse1_word_slots": len(before),
                "source_verse_literal": ref.source_verse_n,
                "resolver_status": ref.status,
                "greek_title_candidate_suppressed": blocked,
                "greek_ref_present": ref.shared_id is not None,
                "source_record_id": doc.source_record_id,
            })
            del doc

    guarded = [r for r in cases if r["greek_title_candidate_suppressed"]]
    if len(cases) != 6 or len(guarded) != 3 or sum(
        r["source_verse1_word_slots"] for r in guarded
    ) != 100:
        raise ValueError("wrong pinned Psalm first-body scope/word partition")
    report = {
        "schema": "bohairic_psalm_verse1_numeric_title_guard_v1",
        "source_coptic_pin": SOURCE_PIN,
        "source_lxx_pin": LXX_PIN,
        "guard_rule": RULE_ID,
        "guarded_source_word_slots": 100,
        "guarded_source_verse1_groups": 3,
        "unaffected_control_groups": 3,
        "cases": cases,
        "interpretation": "Removes invalid same-number Greek TITLE candidate; does not map Coptic source words to Greek translation",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: python tests/live_issue203_psalm_guard.py "
            "PINNED_COPTIC_ROOT PINNED_GREEK_TF OUTPUT_JSON"
        )
    run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
