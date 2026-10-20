"""Bounded whole-source TT scholarly wrapper census (issue #110).

Run with the *existing* pinned sparse corpus checkout of issue #69, avoiding
another 565-blob/2,628-record upstream acquisition. Aggregate annotations,
tag/attribute names and sample physical IDs only, never full text.
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
from copticscriptorium_tf.parser import TAG_RE, _scan_attrs

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
DIRECT = re.compile(r"^[^/]+/[^/]+_TT/[^/]+\.tt$")
ZIPPED = re.compile(r"^[^/]+/[^/]+_TT\.zip$")

# Conservatively classify by *current* source-level native modeling.
MODELED = {
    "meta", "orig_group", "norm_group", "orig", "norm",
    "entity", "translation", "arabic", "arabic_translation",
    "pb_xml_id", "cb_n", "lb_n", "verse_n", "vid_n", "verse_vid",
    "sbl_greek", "sbl_apparatus", "lang",
}
# Do not pretend that a wrapper is harmless merely because parsing succeeds.
REQUIRES_RESEARCH = {"note"}

def audit_tt(
    raw: bytes,
    source_id: str,
    by_tag: Counter,
    inside_norm: Counter,
    by_tag_attr: Counter,
    by_tag_collection: Counter,
    examples: dict[str, list[str]],
    empty_attrs: Counter,
    duplicate_attrs: Counter,
    *,
    watched_examples: dict[tuple[str, str], list[str]] | None = None,
) -> int:
    text = raw.decode("utf-8")
    norm_depth = 0
    source_collection = source_id.split("/", 1)[0]
    openings = 0
    for match in TAG_RE.finditer(text):
        closing, tag = bool(match.group(1)), match.group(2)
        if closing:
            if tag == "norm":
                norm_depth -= 1
                if norm_depth < 0:
                    raise AssertionError(f"unbalanced norm source: {source_id}")
            continue
        attr, duplicates = _scan_attrs(match.group(3), allow_duplicates=True)
        openings += 1
        by_tag[tag] += 1
        by_tag_collection[(tag, source_collection)] += 1
        if norm_depth:
            inside_norm[tag] += 1
        for key, value in attr.items():
            by_tag_attr[(tag, key)] += 1
            if watched_examples is not None and tag == "morph" and key == "lang":
                identifiers = watched_examples.setdefault((tag, key), [])
                if source_id not in identifiers and len(identifiers) < 3:
                    identifiers.append(source_id)
            if value == "":
                empty_attrs[(tag, key)] += 1
        for key, occurrences in duplicates.items():
            duplicate_attrs[(tag, key)] += len(occurrences) - 1
        if tag not in MODELED:
            samples = examples.setdefault(tag, [])
            if source_id not in samples and len(samples) < 3:
                samples.append(source_id)
        if tag == "norm":
            norm_depth += 1
    if norm_depth:
        raise AssertionError(f"unclosed norm source: {source_id}")
    return openings


def run(root: Path) -> None:
    selected = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if DIRECT.fullmatch(rel) or ZIPPED.fullmatch(rel):
            selected.append((rel, path))
        else:
            raise AssertionError(f"unexpected selected Git path {rel}")
    assert len(selected) == 565, f"pinned Git selection is incomplete: {len(selected)}"

    by_tag, inside_norm = Counter(), Counter()
    by_tag_attr, by_tag_collection = Counter(), Counter()
    empty_attrs, duplicate_attrs = Counter(), Counter()
    examples: dict[str, list[str]] = {}
    watched_examples: dict[tuple[str, str], list[str]] = {}
    docs = opens = 0
    for rel, path in sorted(selected):
        corpus = rel.split("/", 1)[0]
        if rel.endswith("_TT.zip"):
            with ZipFile(path) as zf:
                for member in zf.infolist():
                    if member.is_dir() or not member.filename.lower().endswith(".tt"):
                        continue
                    identifier = f"{rel}!{member.filename}"
                    opens += audit_tt(
                        zf.read(member), identifier, by_tag, inside_norm,
                        by_tag_attr, by_tag_collection, examples,
                        empty_attrs, duplicate_attrs,
                        watched_examples=watched_examples,
                    )
                    docs += 1
        else:
            opens += audit_tt(
                path.read_bytes(), rel, by_tag, inside_norm,
                by_tag_attr, by_tag_collection, examples,
                empty_attrs, duplicate_attrs,
                watched_examples=watched_examples,
            )
            docs += 1
    assert docs == 2628, (docs, "pinned source record count mismatch")
    assert by_tag["lang"] >= 77, "source language wrapper coverage unexpectedly absent"
    assert inside_norm["lang"] > 0, "inside-word source language shape lost"

    matrix = []
    for tag, count in sorted(by_tag.items()):
        status = (
            "modeled" if tag in MODELED
            else "requires_modeling" if tag in REQUIRES_RESEARCH
            else "unknown_unmodeled"
        )
        matrix.append({
            "tag": tag, "source_occurrences": count,
            "inside_norm_openings": inside_norm[tag],
            "status": status,
            "source_collections": sum(1 for (t, _c) in by_tag_collection if t == tag),
            "attribute_keys": sorted(key for (t, key) in by_tag_attr if t == tag),
            "present_empty_attributes": sum(n for (t, _key), n in empty_attrs.items() if t == tag),
            "repeated_attribute_surplus": sum(n for (t, _key), n in duplicate_attrs.items() if t == tag),
            "sample_source_records": examples.get(tag, []),
        })
    attribute_watch_tags = ("morph", "norm", "entity", "verse_n", "norm_group", "meta")
    source_attribute_pair_counts = {
        tag: {key: count for (_tag, key), count in sorted(by_tag_attr.items())
              if _tag == tag}
        for tag in attribute_watch_tags
    }
    # These are physical source identifiers, not language words or quotations.
    morph_lang_source_records = watched_examples.get(("morph", "lang"), [])
    print(json.dumps({
        "source_attribute_pair_counts": source_attribute_pair_counts,
        "morph_lang_source_records": morph_lang_source_records,
        "source_commit": PIN,
        "selected_tt_git_blobs": len(selected),
        "source_records": docs,
        "opening_tags_total": opens,
        "language_annotations": by_tag["lang"],
        "unmodeled_tag_types": [row["tag"] for row in matrix if row["status"] != "modeled"],
        "tag_conservation_matrix": matrix,
        "scope": "raw source inventory only, not TF feature coverage certification",
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue110_wrapper_census.py PINNED_TT_ROOT")
    run(Path(sys.argv[1]))
