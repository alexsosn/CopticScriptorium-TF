"""Actual full pinned Coptic TT → CenterBLC/LXX address coverage acceptance (#80).

Reads one TT record at a time, never republishes source Coptic or Greek text.
Only deterministic aggregate metadata / bounded physical record IDs are saved.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import re
import sys
from zipfile import ZipFile

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_module import verify_lxx_parent_feature_blobs
from copticscriptorium_tf.lxx_coverage import (
    COPTIC_SOURCE_PIN,
    CopticLxxCoverageAudit,
)

DIRECT = re.compile(r"^[^/]+/[^/]+_TT/[^/]+\.tt$")
ARCHIVE = re.compile(r"^[^/]+/[^/]+_TT\.zip$")
LXX_GIT_PIN = "f32a98eddf7eb239aa73ab863d70381e416d5076"


def run(coptic_root: Path, lxx_path: Path, output: Path) -> None:
    if output.exists():
        raise ValueError(f"refusing to overwrite coverage report: {output}")
    verify_lxx_parent_feature_blobs(lxx_path)
    api = Fabric(locations=[str(lxx_path)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    if not api or api.F.otype.maxSlot != 623693 or (
        api.F.otype.maxNode != 685732
    ) or len(api.F.otype.s("verse")) != 30371:
        raise ValueError("pinned Greek parent Text-Fabric profile mismatch")

    def lookup(book: str, chapter: int, verse: int) -> int | None:
        node = api.T.nodeFromSection((book, chapter, verse))
        if node is None:
            return None
        if api.F.otype.v(node) != "verse":
            raise ValueError("LXX reference returned a non-verse TF node")
        return node

    def lxx_subverses(verse_node: int) -> tuple[str, ...]:
        # Native LXX subverse nodes may cover all words in a Greek verse.
        # Keep them separate from the existence of the enclosing verse node.
        return tuple(str(node) for node in api.L.d(verse_node, otype="subverse"))

    audit = CopticLxxCoverageAudit(
        source_commit=COPTIC_SOURCE_PIN, lookup=lookup,
        subverse_lookup=lxx_subverses,
    )
    files: list[tuple[str, Path]] = []
    for path in coptic_root.rglob("*"):
        if not path.is_file() or ".git" in path.relative_to(coptic_root).parts:
            continue
        relative = path.relative_to(coptic_root).as_posix()
        if not (DIRECT.fullmatch(relative) or ARCHIVE.fullmatch(relative)):
            raise ValueError(f"unexpected sparse TT source file: {relative}")
        files.append((relative, path))
    files.sort()
    if len(files) != 565:
        raise ValueError(f"unexpected pinned TT Git blob count: {len(files)} / 565")

    for relative, path in files:
        corpus = relative.split("/", 1)[0]
        dataset = path.parent.name.removesuffix("_TT")
        if ARCHIVE.fullmatch(relative):
            dataset = path.name.removesuffix("_TT.zip")
            with ZipFile(path) as archive:
                for member in sorted(archive.infolist(), key=lambda m: m.filename):
                    if member.is_dir() or not member.filename.lower().endswith(".tt"):
                        continue
                    source_id = f"{corpus}/{dataset}:{Path(member.filename).stem}"
                    document = parse_tt_record(
                        archive.read(member),
                        source_record_id=source_id,
                        source_path=f"{relative}!{member.filename}",
                        upstream_repository="CopticScriptorium/corpora",
                        upstream_commit=COPTIC_SOURCE_PIN,
                        packaging="archive",
                    )
                    audit.add(document)
                    del document
        else:
            source_id = f"{corpus}/{dataset}:{path.stem}"
            document = parse_tt_record(
                path.read_bytes(),
                source_record_id=source_id,
                source_path=relative,
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit=COPTIC_SOURCE_PIN,
            )
            audit.add(document)
            del document

    report = audit.report()
    if report["totals"]["source_records"] != 2628:
        raise ValueError("unexpected pinned physical TT record count")
    if report["source_scopes"].get("ot_candidate") != 1574:
        raise ValueError(
            f"unexpected conservative OT scope count: {report['source_scopes']}"
        )
    if report["source_scopes"].get("nt_candidate") != 615:
        raise ValueError("unexpected Coptic NT source-scope denominator")
    if report["source_scopes"].get("undetermined") != 439:
        raise ValueError("unexpected Coptic undetermined source denominator")
    if report["totals"]["verse_position_events"] != 29:
        raise ValueError("missing or reclassified source-internal verse markers")
    anomalies = report["ot_source_anomaly_cases"]
    if anomalies["scanned_ot_records"] != 1574:
        raise ValueError("OT anomaly scope no longer matches pinned source census")
    if anomalies["counts"] != {
        "gapped": 309,
        "missing_or_nonpositive_literal": 153,
    }:
        raise ValueError(
            f"OT anomalous verse-marker census differs from #107: {anomalies['counts']}"
        )
    if len(anomalies["cases"]) != 462:
        raise ValueError("not all 462 OT anomaly occurrences were retained")
    # Avoid conflating verse-zero (often edition-dependent), empty, missing,
    # signed, and non-decimal markup; none authorizes an LXX verse number.
    invalid_classes = anomalies["invalid_literal_classes"]
    if sum(invalid_classes.values()) != 153:
        raise ValueError(
            f"invalid source marker kinds do not reconcile to 153: {invalid_classes}"
        )
    # A zero-literal is a source event, NOT a recoverable Greek verse.
    # Group every pinned event by source hash, physical witness, edition and
    # chapter without omitting non-Psalm negative controls.
    zero_groups = anomalies["zero_literal_source_groups"]
    zero_events = sum(group["marker_count"] for group in zero_groups)
    if zero_events != invalid_classes.get("zero_literal", 0) or zero_events != 153:
        raise ValueError(
            f"source-locked verse-zero group reconciliation failed: "
            f"groups={zero_events}, literal_classes={invalid_classes}"
        )
    if anomalies["zero_literal_source_record_count"] != len(
        {group["source_record_id"] for group in zero_groups}
    ):
        raise ValueError("verse-zero physical source record count inconsistent")
    if sum(anomalies["zero_literal_work_edition_counts"].values()) != zero_events:
        raise ValueError("verse-zero work/edition batch counts do not reconcile")
    if any(
        group["marker_count"] != len(group["markers"])
        or not group["source_sha256"]
        or any(marker["literal"] is None
               or not marker["literal"].isascii()
               or not marker["literal"].isdecimal()
               or int(marker["literal"]) != 0
               for marker in group["markers"])
        for group in zero_groups
    ):
        raise ValueError("verse-zero batch has invalid raw-source evidence")
    if any(
        (case["invalid_literal_class"] is None)
        != (case["kind"] == "gapped")
        for case in anomalies["cases"]
    ):
        raise ValueError("literal subtype lost or invented on an anomalous event")
    # Every source OT positive-number jump must survive a source-byte-locked
    # batch, including gaps with no resolvable Greek book or chapter.
    gap_groups = anomalies["gapped_source_groups"]
    gap_events = [
        (g["source_record_id"], g["source_sha256"],
         g["source_chapter"], m["source_marker_ordinal"])
        for g in gap_groups for m in g["markers"]
    ]
    source_gap_events = [
        (c["source_record_id"], c["source_sha256"],
         c["source_chapter"], c["source_marker_ordinal"])
        for c in anomalies["cases"] if c["kind"] == "gapped"
    ]
    if (
        len(gap_events) != 309
        or len(set(gap_events)) != 309
        or set(gap_events) != set(source_gap_events)
    ):
        raise ValueError("309 exact physical source gap events were lost or duplicated")
    if sum(g["marker_count"] for g in gap_groups) != 309:
        raise ValueError("OT gap source-group event total does not reconcile")
    if anomalies["gapped_source_record_count"] != len({
        g["source_record_id"] for g in gap_groups
    }):
        raise ValueError("OT gap physical source record total does not reconcile")
    if sum(anomalies["gapped_work_edition_counts"].values()) != 309:
        raise ValueError("OT gap work/edition display total does not reconcile")
    structured_work_counts = anomalies["gapped_work_edition_groups"]
    if (
        sum(row["event_count"] for row in structured_work_counts) != 309
        or len({(row["source_cts_work"], row["source_edition"])
                for row in structured_work_counts}) != len(structured_work_counts)
    ):
        raise ValueError("OT gap typed work/edition aggregate lost source identities")
    status_counts = Counter(
        c["greek_status"] for c in anomalies["cases"]
        if c["kind"] == "gapped"
    )
    if dict(sorted(status_counts.items())) != anomalies[
        "gapped_greek_check_status_counts"
    ]:
        raise ValueError("OT gap per-event Greek lookup status total differs")
    address_counts = Counter(
        row["address"] for g in gap_groups for marker in g["markers"]
        for row in marker["greek_missing_intermediate"]
    )
    if dict(sorted(address_counts.items())) != anomalies[
        "gapped_intermediate_address_status_counts"
    ]:
        raise ValueError("Greek intermediate address probes lost source evidence")
    if any(
        marker["missing_count"] != len(marker["greek_missing_intermediate"])
        for g in gap_groups for marker in g["markers"]
        if marker["greek_status"] == "crosschecked_address_only"
    ):
        raise ValueError("an inspected numeric gap has incomplete Greek addresses")
    if any(
        marker["greek_missing_intermediate"]
        for g in gap_groups for marker in g["markers"]
        if marker["greek_status"] != "crosschecked_address_only"
    ):
        raise ValueError("unresolved source gap invented Greek address evidence")
    if any(case["greek_status"] == "not_checked" for case in anomalies["cases"]):
        raise ValueError("LXX source anomaly analysis left cases unchecked")
    if any(case["source_sha256"] is None for case in anomalies["cases"]):
        raise ValueError("source-byte provenance missing from anomaly case")
    topology = report["marker_topology"]
    if topology["source_records"] != 2628:
        raise ValueError("missing source documents in verse-tag topology audit")
    if topology["source_records_with_verse_n"] != 2571:
        raise ValueError("missing source verse marker documents")
    if topology["opening_verse_n_tags"] != 73844:
        raise ValueError("source verse marker occurrence census has drifted")
    if sum(row["source_records"] for row in topology["by_scope"].values()) != 2628:
        raise ValueError("biblical-scope marker audit lost physical TT records")
    if sum(row["opening_verse_n_tags"] for row in topology["by_scope"].values()) != 73844:
        raise ValueError("biblical-scope marker audit lost verse tag occurrences")
    if sum(row["chapter_resets"] for row in topology["by_scope"].values()) != topology["chapter_resets"]:
        raise ValueError("chapter-boundary reset partition lost source occurrences")
    for category, count in topology["categories"].items():
        if sum(row["categories"].get(category, 0)
               for row in topology["by_scope"].values()) != count:
            raise ValueError(f"biblical-scope marker audit differs for {category}")
    report["sparse_git_blobs"] = len(files)
    report["lxx_feature_blobs_verified"] = True
    report["lxx_git_commit_checked_by_ci"] = LXX_GIT_PIN
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "source_records": report["totals"]["source_records"],
        "source_scopes": report["source_scopes"],
        "coptic_ot_word_slots": report["totals"]["ot_candidate_word_slots"],
        "distinct_candidate_lxx_verses": report["totals"]["distinct_candidate_lxx_verses"],
        "ot_reference_statuses": report["ot_reference_statuses"],
        "ot_word_statuses": report["ot_word_statuses"],
        "verse_position_events": report["totals"]["verse_position_events"],
        "marker_topology_categories": topology["categories"],
        "ot_marker_anomaly_counts": anomalies["counts"],
        "ot_invalid_source_literal_classes": invalid_classes,
        "ot_numeric_gap_source_groups": len(gap_groups),
        "ot_numeric_gap_source_records": anomalies["gapped_source_record_count"],
        "ot_gap_greek_check_statuses": anomalies["gapped_greek_check_status_counts"],
        "ot_gap_intermediate_address_statuses": anomalies[
            "gapped_intermediate_address_status_counts"
        ],
        "ot_zero_literal_source_groups": len(zero_groups),
        "ot_zero_literal_source_records": anomalies["zero_literal_source_record_count"],
        "ot_zero_literal_work_edition_counts": anomalies["zero_literal_work_edition_counts"],
        "ot_marker_anomaly_cases": len(anomalies["cases"]),
        "ot_greek_crosscheck_statuses": dict(sorted(Counter(case["greek_status"] for case in anomalies["cases"]).items())),
        "marker_topology_by_scope": {
            scope: {"source_records": row["source_records"],
                    "opening_verse_n_tags": row["opening_verse_n_tags"],
                    "chapter_resets": row["chapter_resets"],
                    "categories": row["categories"]}
            for scope, row in topology["by_scope"].items()
        },
        "opening_verse_n_tags": topology["opening_verse_n_tags"],
        "chapter_markers": topology["chapter_markers"],
        "chapter_resets": topology["chapter_resets"],
        "book_profiles": len(report["candidate_lxx_books"]),
        "work_profiles": len(report["cts_works"]),
        "family_profiles": len(report["families"]),
        "lxx_feature_git_blobs_verified": True,
        "mapping_semantics": "address candidates ONLY, NOT textual equivalence",
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: python tests/live_issue80_full_lxx_coverage.py COPTIC_ROOT LXX_TF OUTPUT_JSON")
    run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
