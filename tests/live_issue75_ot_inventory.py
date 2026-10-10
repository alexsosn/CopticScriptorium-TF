"""Enumerate only metadata/counts of every pinned direct and ZIP TT record.

Intentionally no source text, translation text, XML/JSON semantic blobs, or
automatic inference of Coptic-LXX textual equivalence in the report.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.ot_inventory import classify_biblical_record
from copticscriptorium_tf.parser import TAG_RE, _scan_attrs

UPSTREAM_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
DIRECT = re.compile(r"^[^/]+/[^/]+_TT/[^/]+\.tt$")
ARCHIVE = re.compile(r"^[^/]+/[^/]+_TT\.zip$")
MARKER_TAGS = frozenset({"verse_n", "vid_n", "verse_vid"})


def _metadata_and_verse_count(raw: bytes, identity: str) -> tuple[dict[str, str], int]:
    text = raw.decode("utf-8-sig")
    tags = TAG_RE.finditer(text)
    first = next(tags, None)
    if (
        first is None or first.group(1) or first.group(2) != "meta"
        or text[:first.start()].strip()
    ):
        raise ValueError(f"missing initial TT <meta> for {identity}")
    metadata, _duplicates = _scan_attrs(first.group(3), allow_duplicates=True)
    return metadata, sum(
        tag.group(1) == "" and tag.group(2) == "verse_n" for tag in tags
    )


def inventory_source_tree(
    root: Path, *, expected_blobs: int = 565, expected_records: int = 2628
) -> dict[str, object]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.relative_to(root).parts:
            continue
        relative = path.relative_to(root).as_posix()
        if not (DIRECT.fullmatch(relative) or ARCHIVE.fullmatch(relative)):
            raise ValueError(f"unexpected Git-sparse source file {relative}")
        files.append((relative, path))
    files.sort()
    if len(files) != expected_blobs:
        raise ValueError(f"unexpected TT Git blob count {len(files)} != {expected_blobs}")

    total_statuses: Counter[str] = Counter()
    by_family: dict[str, dict[str, object]] = {}
    records = 0
    verse_record_count = 0

    def add(family: str, physical_identity: str, raw: bytes) -> None:
        nonlocal records, verse_record_count
        metadata, verse_count = _metadata_and_verse_count(raw, physical_identity)
        evidence = classify_biblical_record(family, metadata)
        row = by_family.setdefault(
            family,
            {
                "source_records": 0,
                "verse_markers": 0,
                "records_with_verse_n": 0,
                "missing_book_metadata": 0,
                "missing_chapter_metadata": 0,
                "biblical_scope_counts": Counter(),
                "cts_work_counts": Counter(),
                "literal_book_counts": Counter(),
                "examples": [],
            },
        )
        row["source_records"] += 1
        row["verse_markers"] += verse_count
        row["records_with_verse_n"] += int(verse_count > 0)
        row["missing_book_metadata"] += int(not evidence.book_literal)
        row["missing_chapter_metadata"] += int(not evidence.chapter_literal)
        row["biblical_scope_counts"][evidence.status] += 1
        if evidence.cts_work:
            row["cts_work_counts"][evidence.cts_work] += 1
        if evidence.book_literal:
            row["literal_book_counts"][evidence.book_literal] += 1
        if len(row["examples"]) < 3:
            # Path identifier only, without licensed text or translations.
            row["examples"].append(physical_identity)
        total_statuses[evidence.status] += 1
        verse_record_count += int(verse_count > 0)
        records += 1

    for relative, file in files:
        family = relative.split("/", 1)[0]
        if ARCHIVE.fullmatch(relative):
            with ZipFile(file) as archive:
                for member in sorted(archive.infolist(), key=lambda m: m.filename):
                    if member.is_dir() or not member.filename.lower().endswith(".tt"):
                        continue
                    add(family, f"{relative}!{member.filename}", archive.read(member))
        else:
            add(family, relative, file.read_bytes())

    if records != expected_records:
        raise ValueError(f"unexpected physical TT record count {records} != {expected_records}")

    def finish(row: dict[str, object]) -> dict[str, object]:
        return {
            field: dict(sorted(value.items())) if isinstance(value, Counter) else value
            for field, value in row.items()
        }

    return {
        "schema": "coptic_ot_source_scope_inventory_v1",
        "source_commit": UPSTREAM_COMMIT,
        "sparse_git_blobs": len(files),
        "source_records": records,
        "records_with_verse_n": verse_record_count,
        "biblical_scope_counts": dict(sorted(total_statuses.items())),
        "source_families": {
            family: finish(by_family[family]) for family in sorted(by_family)
        },
        "limitations": (
            "OT/NT are source-metadata candidates, not certified literary "
            "identities, textual correspondences, or a LXX verse crosswalk"
        ),
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue75_ot_inventory.py TT_ROOT OUTPUT_JSON")
    root = Path(sys.argv[1])
    output = Path(sys.argv[2])
    if output.exists():
        raise ValueError(f"refusing to overwrite inventory: {output}")
    report = inventory_source_tree(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "source_commit": report["source_commit"],
        "sparse_git_blobs": report["sparse_git_blobs"],
        "source_records": report["source_records"],
        "records_with_verse_n": report["records_with_verse_n"],
        "source_families": len(report["source_families"]),
        "biblical_scope_counts": report["biblical_scope_counts"],
        "full_metadata_inventory": str(output),
        "scope": "metadata evidence only; no textual/versification alignment",
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
