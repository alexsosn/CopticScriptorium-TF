"""Pinned, full-corpus real-source census for Coptic biblical verse markers.

Read every direct and ZIP TT record once, without retaining corpus models or
copying corpus bytes into artifacts. This is a source-shape + parser regression,
not a claim that Coptic and LXX numbering agree.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re
import sys
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from copticscriptorium_tf.parser import TAG_RE, _visible_piece, parse_tt_record

REV = "3ac067f1709a0012daf39ea8da2fac79980176a5"
DIRECT = re.compile(r"^[^/]+/[^/]+_TT/[^/]+\.tt$")
ZIPPED = re.compile(r"^[^/]+/[^/]+_TT\.zip$")


def scan_markers(raw: bytes, identity: str) -> tuple[Counter, tuple[str, ...]]:
    text = raw.decode("utf-8-sig")
    open_norm = False
    word_chars = 0
    cursor = 0
    counts: Counter = Counter()
    problematic: list[str] = []
    for tag in TAG_RE.finditer(text):
        if open_norm:
            word_chars += len(_visible_piece(text[cursor:tag.start()]))
        cursor = tag.end()
        closing, name = tag.group(1), tag.group(2)
        if name in {"verse_n", "vid_n", "verse_vid"} and not closing:
            counts[name] += 1
            if open_norm:
                if name == "verse_n" or word_chars > 0:
                    problematic.append(
                        f"{identity}: {name} begins at character {word_chars} within norm"
                    )
                else:
                    counts["nested_at_word_start"] += 1
        if name == "norm":
            open_norm = not bool(closing)
            if open_norm:
                word_chars = 0
    return counts, tuple(problematic)


def main(root: Path) -> None:
    files = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    selected = []
    for file in files:
        rel = file.relative_to(root).as_posix()
        if DIRECT.fullmatch(rel) or ZIPPED.fullmatch(rel):
            selected.append((rel, file))
        else:
            raise AssertionError(f"unexpected file from sparse acquisition: {rel}")
    assert len(selected) == 565, f"expected 565 pinned TT Git blobs, got {len(selected)}"
    records = 0
    with_verse_n = 0
    counts: Counter = Counter()
    errors: list[str] = []
    total_errors = 0
    for rel, file in sorted(selected):
        corpus = rel.split("/", 1)[0]
        if rel.endswith("_TT.zip"):
            dataset = file.name.removesuffix("_TT.zip")
            with ZipFile(file) as archive:
                for item in archive.infolist():
                    if item.is_dir() or not item.filename.lower().endswith(".tt"):
                        continue
                    record = Path(item.filename).stem
                    source_id = f"{corpus}/{dataset}:{record}"
                    raw = archive.read(item)
                    seen, problems = scan_markers(raw, f"{rel}!{item.filename}")
                    try:
                        parse_tt_record(
                            raw,
                            source_record_id=source_id,
                            source_path=f"{rel}!{item.filename}",
                            upstream_repository="CopticScriptorium/corpora",
                            upstream_commit=REV,
                            packaging="archive",
                        )
                    except Exception as exc:
                        problems += (f"{rel}!{item.filename}: parser {exc}",)
                    total_errors += len(problems)
                    errors.extend(problems[:max(0, 25 - len(errors))])
                    counts.update(seen)
                    with_verse_n += int(seen["verse_n"] > 0)
                    records += 1
        else:
            dataset = Path(rel).parts[1].removesuffix("_TT")
            record = Path(rel).stem
            raw = file.read_bytes()
            seen, problems = scan_markers(raw, rel)
            try:
                parse_tt_record(
                    raw,
                    source_record_id=f"{corpus}/{dataset}:{record}",
                    source_path=rel,
                    upstream_repository="CopticScriptorium/corpora",
                    upstream_commit=REV,
                )
            except Exception as exc:
                problems += (f"{rel}: parser {exc}",)
            total_errors += len(problems)
            errors.extend(problems[:max(0, 25 - len(errors))])
            counts.update(seen)
            with_verse_n += int(seen["verse_n"] > 0)
            records += 1

    assert records == 2628, f"expected pinned 2,628 documents, observed {records}"
    assert counts["verse_n"] > 0 and counts["vid_n"] > 0 and counts["verse_vid"] > 0
    print(json.dumps({
        "source_git_commit": REV,
        "tf_records_parsed": records,
        "sparse_git_blobs": len(selected),
        "records_with_verse_n": with_verse_n,
        "verse_tag_occurrences": dict(counts),
        "token_internal_verse_markers_unresolved": total_errors,
        "errors_sample": errors,
        "nested_at_word_start": counts["nested_at_word_start"],
        "interpretation": "source shape and conversion safety only, not LXX agreement",
    }, sort_keys=True))
    assert total_errors == 0, f"{total_errors} unsupported marker/parser shapes; see errors_sample"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue69_full_verse_census.py ROOT")
    main(Path(sys.argv[1]))
