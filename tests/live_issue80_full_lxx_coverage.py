"""Actual full pinned Coptic TT → CenterBLC/LXX address coverage acceptance (#80).

Reads one TT record at a time, never republishes source Coptic or Greek text.
Only deterministic aggregate metadata / bounded physical record IDs are saved.
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

    audit = CopticLxxCoverageAudit(source_commit=COPTIC_SOURCE_PIN, lookup=lookup)
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
