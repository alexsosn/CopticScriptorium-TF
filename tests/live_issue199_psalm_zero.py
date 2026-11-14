"""Live exact pinned Bohairic Psalm zero spans versus native LXX verse nodes (#199).

No source text in JSON output, no claim of verse equivalence. Inspect all 151
Psalm physical records from one genuine upstream TT ZIP and negative controls.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_module import verify_lxx_parent_feature_blobs
from copticscriptorium_tf.psalm_zero_boundary import (
    PsalmZeroAudit, inspect_psalm_zero, SOURCE_PIN,
)

LXX_PIN = "f32a98eddf7eb239aa73ab863d70381e416d5076"
SOURCE_ZIP = Path("bohairic.ot/bohairic.ot_TT.zip")
PSALM = re.compile(r"19_Psalmi_(\d{3})\.tt\Z")
LAM = frozenset({"25_Lamentationes_01.tt", "25_Lamentationes_05.tt"})
KNOWN_SOURCE_SHA = {
    1: "d29334067d8fa375a222cc2025ea0bfdaf5e01edc441c5813593f233ec3c1dbe",
    2: "9188ff6e7b83bd731a6dcd3821eafb088c86be88142b6c2822db883b398d1c10",
    3: "cbeb4996b0cd142e888bcd630eaac6123af05d7084d49b614066fa9799b5b9d6",
}


def run(source_root: Path, lxx_tf_dir: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("refusing to overwrite Psalm research report")
    verify_lxx_parent_feature_blobs(lxx_tf_dir)
    greek = Fabric(locations=[str(lxx_tf_dir)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    if not greek or greek.F.otype.maxSlot != 623693 or len(
        greek.F.otype.s("verse")
    ) != 30371:
        raise ValueError("Greek TF Psalm parent release/profile mismatch")

    def lookup(chapter: int, verse: int) -> int | None:
        node = greek.T.nodeFromSection(("Ps", chapter, verse))
        if node is not None and greek.F.otype.v(node) != "verse":
            raise ValueError("Greek Psalm lookup returned a non-verse native node")
        return node

    def subverses(node: int) -> tuple[object, ...]:
        return tuple(greek.L.d(node, otype="subverse"))

    archive_path = source_root / SOURCE_ZIP
    audit = PsalmZeroAudit()
    negative_controls = set()
    seen_archive_names = set()
    with ZipFile(archive_path) as archive:
        for member in sorted(archive.infolist(), key=lambda x: x.filename):
            basename = Path(member.filename).name
            match = PSALM.fullmatch(basename)
            if not match and basename not in LAM:
                continue
            if member.is_dir() or basename in seen_archive_names:
                raise ValueError("duplicate or directory with matched Psalm/Lamentations record")
            seen_archive_names.add(basename)
            source_id = f"bohairic.ot/bohairic.ot:{Path(basename).stem}"
            doc = parse_tt_record(
                archive.read(member),
                source_record_id=source_id,
                source_path=f"{SOURCE_ZIP}!{member.filename}",
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit=SOURCE_PIN,
                packaging="archive",
            )
            if match:
                chapter = int(match.group(1))
                if chapter in KNOWN_SOURCE_SHA and (
                    doc.source_sha256 != KNOWN_SOURCE_SHA[chapter]
                ):
                    raise ValueError("pinned real Psalm TT source sha256 drift")
                row = inspect_psalm_zero(
                    doc, greek_verse=lookup, greek_subverse=subverses
                )
                audit.add(doc, row)
            else:
                if inspect_psalm_zero(doc, greek_verse=lookup) is not None:
                    raise ValueError("Lamentations verse-zero misclassified as Psalm")
                negative_controls.add(basename)
            del doc

    report = audit.report()
    if report["source_records"] != 151 or {
        row["source_chapter"] for row in report["records"]
    } != set(range(1, 152)):
        raise ValueError("not all 151 pinned Bohairic Psalm source records were audited")
    if report["counts"] != {"nonempty_zero_span": 151}:
        raise ValueError("real Psalm zero markers are not all nonempty word spans")
    if report["source_zero_word_slots"] != 1313:
        raise ValueError("real pinned zero-span Coptic word census drifted")
    if any(row["next_source_verse_literal"] != "1" for row in report["records"]):
        raise ValueError("source Psalm zero spans do not all end at literal verse 1")
    if report["greek_next_status"] != {"present": 151}:
        raise ValueError("not all real LXX Psalm first verse nodes were found")
    if any(row["greek_next_subverse_count"] != 1 for row in report["records"]):
        raise ValueError("Greek Psalm first-verse subverse shape differs from pinned profile")
    source_controls = {1: 1, 17: 59, 151: 11}
    for row in report["records"]:
        chapter = row["source_chapter"]
        if chapter in source_controls and row["zero_span_word_count"] != source_controls[chapter]:
            raise ValueError("pinned Psalm chapter diagnostic word span drift")
    if negative_controls != LAM:
        raise ValueError("two source Lamentations verse-zero negative controls missing")
    if any(row["source_words_before_zero"] != 0
           or row["zero_source_marker_ordinal"] != 1
           for row in report["records"]):
        raise ValueError("source verse-zero marker topology contradicts pinned #108 baseline")
    if sum(report["counts"].values()) != 151:
        raise ValueError("Psalm 0 source event partition does not reconcile")
    report["greek_feature_blobs_verified"] = True
    report["negative_controls"] = len(negative_controls)
    report["interpretation"] += "; Greek address presence is NOT textual identity"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "source_records": report["source_records"],
        "source_zero_markers": report["source_zero_markers"],
        "source_zero_word_slots": report["source_zero_word_slots"],
        "counts": report["counts"],
        "greek_next_status": report["greek_next_status"],
        "negative_controls": report["negative_controls"],
        "content": "metadata only, no Coptic/Greek text",
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: python tests/live_issue199_psalm_zero.py "
            "PINNED_COPTIC_ROOT LXX_TF_DIR OUTPUT_JSON"
        )
    run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
