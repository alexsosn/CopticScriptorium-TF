"""Corpus-wide semantic census for Coptic Scriptorium TreeTagger exports.

The upstream ``*.tt`` representation is overlapping SGML, not ordinary XML.  This
module therefore parses only the standalone first ``<meta ...>`` start tag as XML
and treats the remainder as text for conservative layer-presence measurements.
It supports both visible ``*_TT`` directories and opaque ``*_TT.zip`` packages.
"""

from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterable, Iterator
import xml.etree.ElementTree as ET
import zipfile


QUALITY_FIELDS = ("segmentation", "tagging", "parsing", "entities", "identities")
REQUIRED_METADATA = ("corpus", "document_cts_urn", "license", "title")

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
    """Parse one standalone TT ``<meta ...>`` start tag.

    Only this autonomous tag is parsed as XML.  Parsing the complete TT stream as
    XML would be incorrect because layout and linguistic spans may overlap.
    """

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


def _first_meta_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip().lstrip("\ufeff")
        if stripped.startswith("<meta"):
            return stripped
        if stripped:
            # Upstream TT metadata is expected before semantic content.  Stop at the
            # first substantive non-meta line so a later literal is not mistaken for
            # document metadata.
            return None
    return None


def _iter_directory_tt(root: Path) -> Iterator[tuple[str, str, str]]:
    """Yield ``(source_id, packaging, text)`` from visible *_TT directories."""

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
    """Yield TT documents from *_TT.zip packages without extracting them."""

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
    """Yield all direct and archive-packed TT documents deterministically."""

    yield from _iter_directory_tt(root)
    yield from _iter_archive_tt(root)


def _meta_json_summary(root: Path) -> dict[str, Any]:
    path = root / "meta.json"
    if not path.is_file():
        return {
            "present": False,
            "top_level_type": None,
            "top_level_size": None,
            "error": None,
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "present": True,
            "top_level_type": None,
            "top_level_size": None,
            "error": str(exc),
        }

    if isinstance(value, dict):
        top_type = "object"
        size = len(value)
    elif isinstance(value, list):
        top_type = "array"
        size = len(value)
    else:
        top_type = type(value).__name__
        size = None
    return {
        "present": True,
        "top_level_type": top_type,
        "top_level_size": size,
        "error": None,
    }


def _ordered_counter(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def audit_upstream(root: Path | str) -> dict[str, Any]:
    """Build a deterministic semantic census for one pinned upstream checkout."""

    root_path = Path(root)
    packaging: Counter[str] = Counter()
    metadata_keys: Counter[str] = Counter()
    quality: dict[str, Counter[str]] = {field: Counter() for field in QUALITY_FIELDS}
    licenses: Counter[str] = Counter()
    redundant: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    layers: Counter[str] = Counter()
    errors: list[dict[str, str]] = []
    documents: list[dict[str, Any]] = []

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
        if meta_line is None:
            errors.append({"kind": "missing_meta", "source": source_id})
        else:
            try:
                attrs = parse_meta_line(meta_line)
            except ValueError as exc:
                errors.append(
                    {"kind": "malformed_meta", "source": source_id, "detail": str(exc)}
                )

        if attrs is not None:
            metadata_keys.update(attrs.keys())
            for field in QUALITY_FIELDS:
                value = attrs.get(field)
                if value:
                    quality[field][value] += 1
                else:
                    missing[field] += 1
            for field in REQUIRED_METADATA:
                if not attrs.get(field):
                    missing[field] += 1
            license_value = attrs.get("license")
            if license_value:
                licenses[license_value] += 1
            redundant_value = attrs.get("redundant")
            if redundant_value:
                redundant[redundant_value] += 1
            else:
                missing["redundant"] += 1

        documents.append(
            {
                "source": source_id,
                "packaging": packaging_kind,
                "corpus": attrs.get("corpus") if attrs else None,
                "document_cts_urn": attrs.get("document_cts_urn") if attrs else None,
            }
        )

    document_count = len(documents)
    all_missing_fields = sorted(set(REQUIRED_METADATA) | set(QUALITY_FIELDS) | {"redundant"})
    missing_metadata = {field: missing[field] for field in all_missing_fields}
    layer_presence = {layer: layers[layer] for layer in sorted(LAYER_PATTERNS)}

    return {
        "document_count": document_count,
        "source_packaging": _ordered_counter(packaging),
        "metadata_key_presence": _ordered_counter(metadata_keys),
        "quality_values": {
            field: _ordered_counter(quality[field]) for field in QUALITY_FIELDS
        },
        "license_values": _ordered_counter(licenses),
        "redundant_values": _ordered_counter(redundant),
        "missing_metadata": missing_metadata,
        "layer_presence": layer_presence,
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
