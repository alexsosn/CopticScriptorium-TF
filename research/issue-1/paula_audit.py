"""Corpus-wide PAULA package and semantic-shape audit.

This research tool inventories pinned Coptic Scriptorium PAULA exports without
making PAULA a production parser. It balances package representations, parses
standard PAULA XML members, records list/body kinds and annotation types, and
surfaces metadata feature files (feature lists based on ``*.anno.xml``).
Malformed XML and unsupported package shapes remain explicit evidence.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Iterator
import xml.etree.ElementTree as ET
import zipfile


XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"
CONTENT_KINDS = {
    "body",
    "markList",
    "featList",
    "multiFeatList",
    "structList",
    "relList",
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _ordered(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _dataset_for_archive(root: Path, archive_path: Path) -> tuple[str, str]:
    relative = archive_path.relative_to(root)
    parts = relative.parts
    if len(parts) == 2 and parts[1].endswith("_PAULA.zip"):
        corpus = parts[0]
        dataset_name = parts[1][:-10]
        return f"{corpus}/{dataset_name}", relative.as_posix()
    if (
        len(parts) == 3
        and parts[1].endswith("_PAULA")
        and parts[2].endswith("_PAULA.zip")
    ):
        corpus = parts[0]
        dataset_name = parts[1][:-6]
        return f"{corpus}/{dataset_name}", relative.as_posix()
    raise ValueError(f"unsupported PAULA archive location: {relative.as_posix()}")


def _dataset_for_directory(root: Path, directory: Path) -> tuple[str, str]:
    relative = directory.relative_to(root)
    parts = relative.parts
    if len(parts) != 2 or not parts[1].endswith("_PAULA"):
        raise ValueError(f"unsupported PAULA directory location: {relative.as_posix()}")
    corpus = parts[0]
    dataset_name = parts[1][:-6]
    return f"{corpus}/{dataset_name}", relative.as_posix()


def _packages(root: Path) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    archive_paths = sorted(root.rglob("*_PAULA.zip"), key=lambda path: path.as_posix())
    archive_parents = {path.parent.resolve() for path in archive_paths}

    for archive_path in archive_paths:
        dataset, source = _dataset_for_archive(root, archive_path)
        packages.append(
            {
                "dataset": dataset,
                "source": source,
                "packaging": "archive",
                "path": archive_path,
            }
        )

    for directory in sorted(
        (path for path in root.rglob("*_PAULA") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        # A wrapper directory containing the actual *_PAULA.zip is one package,
        # not a directory package plus an archive package.
        if directory.resolve() in archive_parents:
            continue
        dataset, source = _dataset_for_directory(root, directory)
        packages.append(
            {
                "dataset": dataset,
                "source": source,
                "packaging": "directory",
                "path": directory,
            }
        )

    indexed: dict[str, dict[str, Any]] = {}
    for package in packages:
        dataset = package["dataset"]
        if dataset in indexed:
            previous = indexed[dataset]
            raise ValueError(
                f"duplicate PAULA package representation for {dataset}: "
                f"{previous['source']} versus {package['source']}"
            )
        indexed[dataset] = package
    return [indexed[key] for key in sorted(indexed)]


def _archive_members(package: dict[str, Any]) -> Iterator[tuple[str, bytes]]:
    path: Path = package["path"]
    source = package["source"]
    with zipfile.ZipFile(path) as archive:
        for member in sorted(archive.namelist()):
            if member.endswith("/") or not member.lower().endswith(".xml"):
                continue
            yield f"{source}!/{member}", archive.read(member)


def _directory_members(root: Path, package: dict[str, Any]) -> Iterator[tuple[str, bytes]]:
    path: Path = package["path"]
    for member in sorted(path.rglob("*.xml"), key=lambda item: item.as_posix()):
        yield member.relative_to(root).as_posix(), member.read_bytes()


def _content_element(root_element: ET.Element) -> ET.Element:
    content = [
        child
        for child in root_element
        if _local_name(child.tag) in CONTENT_KINDS
    ]
    if len(content) != 1:
        kinds = [_local_name(child.tag) for child in content]
        raise ValueError(
            "expected exactly one PAULA content element; found "
            + (", ".join(kinds) if kinds else "none")
        )
    return content[0]


def _header_id(root_element: ET.Element) -> str | None:
    for child in root_element:
        if _local_name(child.tag) == "header":
            return child.attrib.get("paula_id")
    return None


def _feature_values(content: ET.Element) -> list[str]:
    values: list[str] = []
    for child in content:
        if _local_name(child.tag) == "feat" and "value" in child.attrib:
            values.append(child.attrib["value"])
    return values


def audit_upstream(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    packages = _packages(root_path)

    packaging: Counter[str] = Counter()
    element_kinds: Counter[str] = Counter()
    list_types: dict[str, Counter[str]] = defaultdict(Counter)
    metadata_types: Counter[str] = Counter()
    metadata_instances: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    xml_member_count = 0
    parsed_package_count = 0

    for package in packages:
        packaging[package["packaging"]] += 1
        package_opened = False
        try:
            if package["packaging"] == "archive":
                members = list(_archive_members(package))
            else:
                members = list(_directory_members(root_path, package))
            package_opened = True
        except (OSError, zipfile.BadZipFile) as exc:
            errors.append(
                {
                    "kind": "unreadable_package",
                    "source": package["source"],
                    "detail": str(exc),
                }
            )
            continue

        if package_opened:
            parsed_package_count += 1
        if not members:
            errors.append(
                {
                    "kind": "unsupported_package_shape",
                    "source": package["source"],
                    "detail": "no PAULA XML members",
                }
            )
            continue

        for source, raw in members:
            xml_member_count += 1
            try:
                root_element = ET.fromstring(raw)
            except (ET.ParseError, UnicodeDecodeError) as exc:
                errors.append(
                    {"kind": "malformed_xml", "source": source, "detail": str(exc)}
                )
                continue

            if _local_name(root_element.tag) != "paula":
                errors.append(
                    {
                        "kind": "invalid_root",
                        "source": source,
                        "detail": f"expected paula root, got {_local_name(root_element.tag)!r}",
                    }
                )
                continue

            try:
                content = _content_element(root_element)
            except ValueError as exc:
                errors.append(
                    {"kind": "invalid_content", "source": source, "detail": str(exc)}
                )
                continue

            kind = _local_name(content.tag)
            element_kinds[kind] += 1
            list_type = content.attrib.get("type")
            if kind != "body" and list_type:
                list_types[kind][list_type] += 1

            if kind == "featList":
                base = content.attrib.get(XML_BASE) or content.attrib.get("xml:base")
                if base and Path(base).name.endswith(".anno.xml") and list_type:
                    metadata_types[list_type] += 1
                    metadata_instances.append(
                        {
                            "dataset": package["dataset"],
                            "source": source,
                            "paula_id": _header_id(root_element),
                            "base": base,
                            "type": list_type,
                            "values": _feature_values(content),
                        }
                    )

    return {
        "source_package_count": len(packages),
        "parsed_package_count": parsed_package_count,
        "datasets": [package["dataset"] for package in packages],
        "packaging": _ordered(packaging),
        "xml_member_count": xml_member_count,
        "element_kind_counts": _ordered(element_kinds),
        "list_type_occurrences": {
            kind: _ordered(list_types[kind]) for kind in sorted(list_types)
        },
        "metadata_feature_type_occurrences": _ordered(metadata_types),
        "metadata_feature_instances": sorted(
            metadata_instances,
            key=lambda item: (
                item["dataset"],
                item["source"],
                item.get("type") or "",
                item.get("paula_id") or "",
            ),
        ),
        "errors": sorted(
            errors,
            key=lambda error: (
                error.get("source", ""),
                error.get("kind", ""),
                error.get("detail", ""),
            ),
        ),
    }


def render_report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path, help="Pinned Coptic Scriptorium checkout")
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
