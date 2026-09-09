"""Reconcile Coptic Scriptorium global meta.json with TT document metadata.

The upstream meta.json is keyed by source-record basename, while the same scholarly
record can appear in more than one TT corpus (for example source corpus plus the
coptic-treebank convenience corpus). This audit therefore permits multiple TT
copies per global metadata key, rejects ambiguous case-insensitive meta.json keys,
and measures disagreements and asymmetric field coverage without resolving them.
"""

from __future__ import annotations

from collections import Counter
import argparse
import html
import json
from pathlib import Path
import re
from typing import Any, Iterator
import zipfile


META_ATTRIBUTE_RE = re.compile(
    r'\s+([A-Za-z_][A-Za-z0-9_.:-]*)\s*=\s*"([^"]*)"'
)


def _scan_meta_line(line: str) -> dict[str, str]:
    stripped = line.strip().lstrip("\ufeff")
    if not stripped.startswith("<meta") or not stripped.endswith(">"):
        raise ValueError("not a complete <meta ...> start tag")
    body_end = -2 if stripped.endswith("/>") else -1
    body = stripped[len("<meta") : body_end]
    position = 0
    attrs: dict[str, str] = {}
    while position < len(body):
        if body[position:].strip() == "":
            break
        match = META_ATTRIBUTE_RE.match(body, position)
        if match is None:
            raise ValueError(f"malformed meta attribute syntax near offset {position}")
        name = match.group(1)
        value = html.unescape(match.group(2))
        attrs.setdefault(name, value)
        position = match.end()
    return attrs


def _first_meta_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip().lstrip("\ufeff")
        if stripped.startswith("<meta"):
            return stripped
        if stripped:
            return None
    return None


def _iter_direct_tt(root: Path) -> Iterator[dict[str, Any]]:
    for directory in sorted(
        (path for path in root.rglob("*_TT") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        for path in sorted(directory.rglob("*.tt"), key=lambda p: p.as_posix()):
            text = path.read_text(encoding="utf-8")
            meta_line = _first_meta_line(text)
            attrs = _scan_meta_line(meta_line) if meta_line is not None else {}
            yield {
                "source": path.relative_to(root).as_posix(),
                "record": path.stem,
                "attributes": attrs,
            }


def _iter_archive_tt(root: Path) -> Iterator[dict[str, Any]]:
    for archive_path in sorted(root.rglob("*_TT.zip"), key=lambda p: p.as_posix()):
        archive_rel = archive_path.relative_to(root).as_posix()
        with zipfile.ZipFile(archive_path) as archive:
            for member in sorted(archive.namelist()):
                if member.endswith("/") or not member.lower().endswith(".tt"):
                    continue
                text = archive.read(member).decode("utf-8")
                meta_line = _first_meta_line(text)
                attrs = _scan_meta_line(meta_line) if meta_line is not None else {}
                yield {
                    "source": f"{archive_rel}!/{member}",
                    "record": Path(member).stem,
                    "attributes": attrs,
                }


def _iter_tt(root: Path) -> Iterator[dict[str, Any]]:
    yield from _iter_direct_tt(root)
    yield from _iter_archive_tt(root)


def _load_meta_json(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    path = root / "meta.json"
    if not path.is_file():
        raise ValueError("meta.json is missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("meta.json top level must be an object")

    technical_to_literal: dict[str, str] = {}
    for literal in value:
        technical = str(literal).casefold()
        if technical in technical_to_literal:
            previous = technical_to_literal[technical]
            raise ValueError(
                "meta.json case-insensitive key collision: "
                f"{previous!r} versus {literal!r}"
            )
        technical_to_literal[technical] = str(literal)
    return value, technical_to_literal


def _scalar_text(value: Any) -> str | None:
    if isinstance(value, (dict, list)):
        return None
    return "" if value is None else str(value)


def audit_upstream(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    meta, meta_index = _load_meta_json(root_path)
    documents = sorted(_iter_tt(root_path), key=lambda item: item["source"])

    matched_count = 0
    used_meta_keys: set[str] = set()
    tt_without: list[dict[str, str]] = []
    copy_counts: Counter[str] = Counter()
    mismatch_counts: Counter[str] = Counter()
    mismatch_examples: list[dict[str, Any]] = []
    meta_missing_in_tt_counts: Counter[str] = Counter()
    tt_missing_in_meta_counts: Counter[str] = Counter()
    meta_missing_in_tt_examples: list[dict[str, Any]] = []
    tt_missing_in_meta_examples: list[dict[str, Any]] = []

    for document in documents:
        technical = document["record"].casefold()
        literal_key = meta_index.get(technical)
        if literal_key is None:
            tt_without.append(
                {"record": document["record"], "source": document["source"]}
            )
            continue

        matched_count += 1
        used_meta_keys.add(literal_key)
        copy_counts[literal_key] += 1
        meta_value = meta[literal_key]
        if not isinstance(meta_value, dict):
            continue

        attrs = document["attributes"]

        for field in sorted(set(meta_value) - set(attrs)):
            json_text = _scalar_text(meta_value[field])
            if json_text is None:
                continue
            meta_missing_in_tt_counts[field] += 1
            if len(meta_missing_in_tt_examples) < 100:
                meta_missing_in_tt_examples.append(
                    {
                        "record": literal_key,
                        "source": document["source"],
                        "field": field,
                        "meta_json": json_text,
                    }
                )

        for field in sorted(set(attrs) - set(meta_value)):
            tt_missing_in_meta_counts[field] += 1
            if len(tt_missing_in_meta_examples) < 100:
                tt_missing_in_meta_examples.append(
                    {
                        "record": literal_key,
                        "source": document["source"],
                        "field": field,
                        "tt": attrs[field],
                    }
                )

        for field in sorted(set(attrs) & set(meta_value)):
            tt_value = attrs[field]
            json_text = _scalar_text(meta_value[field])
            if json_text is None or tt_value == json_text:
                continue
            mismatch_counts[field] += 1
            if len(mismatch_examples) < 100:
                mismatch_examples.append(
                    {
                        "record": literal_key,
                        "source": document["source"],
                        "field": field,
                        "tt": tt_value,
                        "meta_json": json_text,
                    }
                )

    orphan = sorted(str(key) for key in meta if str(key) not in used_meta_keys)
    reconciliation = {
        "matched_tt_document_count": matched_count,
        "tt_without_meta_json": sorted(
            tt_without, key=lambda item: (item["record"], item["source"])
        ),
        "meta_json_without_tt": orphan,
        "record_copy_counts": {
            key: copy_counts[key] for key in sorted(copy_counts)
        },
        "field_mismatch_counts": {
            key: mismatch_counts[key] for key in sorted(mismatch_counts)
        },
        "field_mismatch_examples": mismatch_examples,
        "meta_fields_missing_in_tt_counts": {
            key: meta_missing_in_tt_counts[key]
            for key in sorted(meta_missing_in_tt_counts)
        },
        "meta_fields_missing_in_tt_examples": meta_missing_in_tt_examples,
        "tt_fields_missing_in_meta_counts": {
            key: tt_missing_in_meta_counts[key]
            for key in sorted(tt_missing_in_meta_counts)
        },
        "tt_fields_missing_in_meta_examples": tt_missing_in_meta_examples,
    }
    return {
        "tt_document_count": len(documents),
        "meta_json": {
            "present": True,
            "top_level_type": "object",
            "top_level_size": len(meta),
            "reconciliation": reconciliation,
        },
    }


def render_report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    rendered = render_report_json(audit_upstream(args.upstream))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
