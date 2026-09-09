"""Corpus-wide semantic census for Coptic Scriptorium TreeTagger exports.

The upstream ``*.tt`` representation is overlapping SGML, not ordinary XML. This
module therefore treats the document stream as text. The standalone first
``<meta ...>`` line is parsed both with a strict XML helper (useful for fixtures and
well-formed records) and with a source-native attribute lexer that preserves real
upstream duplicate attributes instead of silently overwriting them.

Both visible ``*_TT`` directories and opaque ``*_TT.zip`` packages are supported.
"""

from __future__ import annotations

from collections import Counter
import argparse
import html
import json
from pathlib import Path
import re
from typing import Any, Iterator
import xml.etree.ElementTree as ET
import zipfile


QUALITY_FIELDS = ("segmentation", "tagging", "parsing", "entities", "identities")
REQUIRED_METADATA = ("corpus", "document_cts_urn", "license", "title")
META_NAME_RE = r"[A-Za-z_][A-Za-z0-9_.:-]*"
META_ATTRIBUTE_RE = re.compile(rf'\s+({META_NAME_RE})\s*=\s*"([^"]*)"')

LAYER_PATTERNS: dict[str, re.Pattern[str]] = {
    "orig_group": re.compile(r"<orig_group\b"),
    "norm_group": re.compile(r"<norm_group\b"),
    "orig": re.compile(r"<orig\b"),
    "norm": re.compile(r"<norm\b"),
    "dependency_xml_id": re.compile(r"<norm\b[^>]*\bxml:id\s*="),
    "dependency_func": re.compile(r"<norm\b[^>]*\bfunc\s*="),
    "dependency_head": re.compile(r"<norm\b[^>]*\bhead\s*="),
    "entity": re.compile(r"<entity\b"),
    "entity_identity": re.compile(r"<entity\b[^>]*\bidentity\s*="),
    "entity_head_tok": re.compile(r"<entity\b[^>]*\bhead_tok\s*="),
    "translation": re.compile(r"<translation\b"),
    "arabic_translation": re.compile(r"<(?:arabic|arabic_translation)\b"),
    "page": re.compile(r"<(?:pb|pb_[A-Za-z0-9_]+)\b"),
    "column": re.compile(r"<(?:cb|cb_[A-Za-z0-9_]+)\b"),
    "line": re.compile(r"<(?:lb|lb_[A-Za-z0-9_]+)\b"),
}


def parse_meta_line(line: str) -> dict[str, str]:
    """Strictly parse one XML-well-formed TT ``<meta ...>`` start tag."""

    stripped = line.strip().lstrip("\ufeff")
    if not stripped.startswith("<meta") or not stripped.endswith(">"):
        raise ValueError("not a complete <meta ...> start tag")
    if stripped.endswith("/>"):
        xml = stripped
    else:
        xml = stripped[:-1] + "/>"
    try:
        element = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError(f"malformed meta tag: {exc}") from exc
    if element.tag != "meta":
        raise ValueError(f"expected meta tag, got {element.tag!r}")
    return dict(element.attrib)


def scan_meta_line(line: str) -> dict[str, Any]:
    """Lex a source TT meta line while preserving duplicate attributes.

    Coptic Scriptorium contains meta tags with repeated XML attribute names. They
    are invalid XML but have an unambiguous SGML-like surface grammar: whitespace,
    an attribute name, optional whitespace around ``=``, and a double-quoted value.
    This lexer validates that the complete line conforms to that grammar, decodes
    character references, and reports every repeated value. The first literal value
    is exposed in ``attributes`` for census calculations; duplicate/conflict
    information remains explicit so production conversion cannot mistake that
    choice for a resolution policy.
    """

    stripped = line.strip().lstrip("\ufeff")
    if not stripped.startswith("<meta") or not stripped.endswith(">"):
        raise ValueError("not a complete <meta ...> start tag")

    body_end = -2 if stripped.endswith("/>") else -1
    body = stripped[len("<meta") : body_end]
    position = 0
    pairs: list[tuple[str, str]] = []

    while position < len(body):
        if body[position:].strip() == "":
            break
        match = META_ATTRIBUTE_RE.match(body, position)
        if match is None:
            column = len("<meta") + position + 1
            raise ValueError(f"malformed meta attribute syntax near column {column}")
        name = match.group(1)
        value = html.unescape(match.group(2))
        pairs.append((name, value))
        position = match.end()

    if not pairs and body.strip():
        raise ValueError("malformed meta attribute syntax")

    values_by_name: dict[str, list[str]] = {}
    attributes: dict[str, str] = {}
    for name, value in pairs:
        values_by_name.setdefault(name, []).append(value)
        attributes.setdefault(name, value)

    duplicates = {
        name: {
            "values": values,
            "conflict": len(set(values)) > 1,
        }
        for name, values in sorted(values_by_name.items())
        if len(values) > 1
    }
    return {"attributes": attributes, "duplicates": duplicates}


def _first_meta_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip().lstrip("\ufeff")
        if stripped.startswith("<meta"):
            return stripped
        if stripped:
            return None
    return None


def _iter_directory_tt(root: Path) -> Iterator[tuple[str, str, str]]:
    for directory in sorted(
        (path for path in root.rglob("*_TT") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        for path in sorted(directory.rglob("*.tt"), key=lambda item: item.as_posix()):
            source_id = path.relative_to(root).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = path.read_text(encoding="utf-8", errors="replace")
            yield source_id, "directory", text


def _iter_archive_tt(root: Path) -> Iterator[tuple[str, str, str]]:
    for archive_path in sorted(root.rglob("*_TT.zip"), key=lambda path: path.as_posix()):
        archive_rel = archive_path.relative_to(root).as_posix()
        with zipfile.ZipFile(archive_path) as archive:
            members = sorted(
                name
                for name in archive.namelist()
                if not name.endswith("/") and name.lower().endswith(".tt")
            )
            for member in members:
                raw = archive.read(member)
                text = raw.decode("utf-8", errors="replace")
                yield f"{archive_rel}!/{member}", "archive", text


def iter_tt_documents(root: Path) -> Iterator[tuple[str, str, str]]:
    yield from _iter_directory_tt(root)
    yield from _iter_archive_tt(root)


def _shape_of(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "type": "object",
            "size": len(value),
            "keys": sorted(str(key) for key in value)[:20],
        }
    if isinstance(value, list):
        return {"type": "array", "size": len(value)}
    return {"type": type(value).__name__, "value": value}


def _meta_json_summary(root: Path) -> dict[str, Any]:
    path = root / "meta.json"
    if not path.is_file():
        return {
            "present": False,
            "top_level_type": None,
            "top_level_size": None,
            "sample_keys": [],
            "sample_entries": [],
            "error": None,
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "present": True,
            "top_level_type": None,
            "top_level_size": None,
            "sample_keys": [],
            "sample_entries": [],
            "error": str(exc),
        }

    sample_keys: list[str] = []
    sample_entries: list[dict[str, Any]] = []
    if isinstance(value, dict):
        top_type = "object"
        size = len(value)
        ordered_keys = sorted(value, key=lambda key: str(key))
        sample_keys = [str(key) for key in ordered_keys[:10]]
        sample_entries = [
            {"key": str(key), "value_shape": _shape_of(value[key])}
            for key in ordered_keys[:3]
        ]
    elif isinstance(value, list):
        top_type = "array"
        size = len(value)
        sample_entries = [
            {"index": index, "value_shape": _shape_of(item)}
            for index, item in enumerate(value[:3])
        ]
    else:
        top_type = type(value).__name__
        size = None
        sample_entries = [{"value_shape": _shape_of(value)}]
    return {
        "present": True,
        "top_level_type": top_type,
        "top_level_size": size,
        "sample_keys": sample_keys,
        "sample_entries": sample_entries,
        "error": None,
    }


def _ordered_counter(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def audit_upstream(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    packaging: Counter[str] = Counter()
    metadata_keys: Counter[str] = Counter()
    quality: dict[str, Counter[str]] = {field: Counter() for field in QUALITY_FIELDS}
    licenses: Counter[str] = Counter()
    redundant: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    missing_records: list[dict[str, str | None]] = []
    layers: Counter[str] = Counter()
    errors: list[dict[str, str]] = []
    documents: list[dict[str, Any]] = []

    duplicate_document_count = 0
    duplicate_equal_count = 0
    duplicate_conflict_count = 0
    duplicate_key_documents: Counter[str] = Counter()
    duplicate_conflicts: list[dict[str, Any]] = []

    for source_id, packaging_kind, text in iter_tt_documents(root_path):
        packaging[packaging_kind] += 1
        layer_flags = {
            layer: bool(pattern.search(text)) for layer, pattern in LAYER_PATTERNS.items()
        }
        for layer, present in layer_flags.items():
            if present:
                layers[layer] += 1

        meta_line = _first_meta_line(text)
        attrs: dict[str, str] | None = None
        duplicates: dict[str, dict[str, Any]] = {}
        if meta_line is None:
            errors.append({"kind": "missing_meta", "source": source_id})
        else:
            try:
                scanned = scan_meta_line(meta_line)
                attrs = scanned["attributes"]
                duplicates = scanned["duplicates"]
            except ValueError as exc:
                errors.append(
                    {"kind": "malformed_meta", "source": source_id, "detail": str(exc)}
                )

        if duplicates:
            duplicate_document_count += 1
            for key, duplicate in sorted(duplicates.items()):
                duplicate_key_documents[key] += 1
                if duplicate["conflict"]:
                    duplicate_conflict_count += 1
                    duplicate_conflicts.append(
                        {"source": source_id, "key": key, "values": duplicate["values"]}
                    )
                else:
                    duplicate_equal_count += 1

        if attrs is not None:
            metadata_keys.update(attrs.keys())

            def record_missing(field: str) -> None:
                missing[field] += 1
                missing_records.append(
                    {
                        "field": field,
                        "source": source_id,
                        "corpus": attrs.get("corpus"),
                        "document_cts_urn": attrs.get("document_cts_urn"),
                    }
                )

            for field in QUALITY_FIELDS:
                value = attrs.get(field)
                if value:
                    quality[field][value] += 1
                else:
                    record_missing(field)
            for field in REQUIRED_METADATA:
                if not attrs.get(field):
                    record_missing(field)
            license_value = attrs.get("license")
            if license_value:
                licenses[license_value] += 1
            redundant_value = attrs.get("redundant")
            if redundant_value:
                redundant[redundant_value] += 1
            else:
                record_missing("redundant")

        documents.append(
            {
                "source": source_id,
                "packaging": packaging_kind,
                "corpus": attrs.get("corpus") if attrs else None,
                "document_cts_urn": attrs.get("document_cts_urn") if attrs else None,
            }
        )

    all_missing_fields = sorted(set(REQUIRED_METADATA) | set(QUALITY_FIELDS) | {"redundant"})
    return {
        "document_count": len(documents),
        "source_packaging": _ordered_counter(packaging),
        "metadata_key_presence": _ordered_counter(metadata_keys),
        "quality_values": {
            field: _ordered_counter(quality[field]) for field in QUALITY_FIELDS
        },
        "license_values": _ordered_counter(licenses),
        "redundant_values": _ordered_counter(redundant),
        "missing_metadata": {field: missing[field] for field in all_missing_fields},
        "missing_metadata_records": sorted(
            missing_records,
            key=lambda item: (
                item["field"] or "",
                item["source"] or "",
                item["corpus"] or "",
                item["document_cts_urn"] or "",
            ),
        ),
        "layer_presence": {layer: layers[layer] for layer in sorted(LAYER_PATTERNS)},
        "duplicate_meta_attributes": {
            "document_count": duplicate_document_count,
            "equal_value_occurrences": duplicate_equal_count,
            "conflicting_occurrences": duplicate_conflict_count,
            "key_document_counts": _ordered_counter(duplicate_key_documents),
            "conflict_examples": sorted(
                duplicate_conflicts,
                key=lambda item: (item["source"], item["key"]),
            )[:50],
        },
        "meta_json": _meta_json_summary(root_path),
        "errors": sorted(
            errors,
            key=lambda error: (
                error.get("source", ""),
                error.get("kind", ""),
                error.get("detail", ""),
            ),
        ),
        "documents": sorted(documents, key=lambda document: document["source"]),
    }


def render_report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path, help="Pinned CopticScriptorium/corpora checkout")
    parser.add_argument("--output", type=Path, help="Write report here instead of stdout")
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
