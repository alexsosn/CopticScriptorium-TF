"""Corpus-wide PAULA package and semantic-shape audit."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from io import BytesIO
import json
from pathlib import Path
from typing import Any, Iterator
import xml.etree.ElementTree as ET
import zipfile


XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"
CONTENT_KINDS = {"body", "markList", "featList", "multiFeatList", "structList", "relList"}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _ordered(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _dataset_for_archive(root: Path, path: Path) -> tuple[str, str]:
    relative = path.relative_to(root)
    parts = relative.parts
    if len(parts) == 2 and parts[1].endswith("_PAULA.zip"):
        return f"{parts[0]}/{parts[1][:-10]}", relative.as_posix()
    if len(parts) == 3 and parts[1].endswith("_PAULA") and parts[2].endswith("_PAULA.zip"):
        return f"{parts[0]}/{parts[1][:-6]}", relative.as_posix()
    raise ValueError(f"unsupported PAULA archive location: {relative.as_posix()}")


def _dataset_for_directory(root: Path, path: Path) -> tuple[str, str]:
    relative = path.relative_to(root)
    parts = relative.parts
    if len(parts) != 2 or not parts[1].endswith("_PAULA"):
        raise ValueError(f"unsupported PAULA directory location: {relative.as_posix()}")
    return f"{parts[0]}/{parts[1][:-6]}", relative.as_posix()


def _packages(root: Path) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    archives = sorted(root.rglob("*_PAULA.zip"), key=lambda path: path.as_posix())
    archive_parents = {path.parent.resolve() for path in archives}

    for path in archives:
        dataset, source = _dataset_for_archive(root, path)
        packages.append({"dataset": dataset, "source": source, "packaging": "archive", "path": path})

    for path in sorted(
        (candidate for candidate in root.rglob("*_PAULA") if candidate.is_dir()),
        key=lambda candidate: candidate.as_posix(),
    ):
        if path.resolve() in archive_parents:
            continue
        dataset, source = _dataset_for_directory(root, path)
        packages.append({"dataset": dataset, "source": source, "packaging": "directory", "path": path})

    indexed: dict[str, dict[str, Any]] = {}
    for package in packages:
        dataset = package["dataset"]
        if dataset in indexed:
            raise ValueError(f"duplicate PAULA package representation for {dataset}")
        indexed[dataset] = package
    return [indexed[key] for key in sorted(indexed)]


def _xml_members_from_zip(archive: zipfile.ZipFile, source_prefix: str) -> list[tuple[str, bytes]]:
    return [
        (f"{source_prefix}!/{member}", archive.read(member))
        for member in sorted(archive.namelist())
        if not member.endswith("/") and member.lower().endswith(".xml")
    ]


def _archive_members(package: dict[str, Any]) -> Iterator[tuple[str, bytes]]:
    """Yield XML from an ordinary PAULA ZIP or one observed one-level wrapper.

    Bohairic aggregate packages in the pinned source contain exactly one inner
    ``*_PAULA.zip`` instead of XML at the outer level. We support that measured
    shape only. Mixed direct-XML-plus-wrapper payloads, multiple inner archives,
    unrelated ZIPs, or deeper wrappers are deliberately not guessed through.
    """

    with zipfile.ZipFile(package["path"]) as outer:
        direct_xml = _xml_members_from_zip(outer, package["source"])
        inner_archives = sorted(
            member
            for member in outer.namelist()
            if not member.endswith("/") and Path(member).name.lower().endswith("_paula.zip")
        )

        if direct_xml and inner_archives:
            raise ValueError(
                f"mixed PAULA archive contains direct XML and inner *_PAULA.zip: {package['source']}"
            )
        if direct_xml:
            yield from direct_xml
            return
        if len(inner_archives) != 1:
            return

        inner_name = inner_archives[0]
        inner_source = f"{package['source']}!/{inner_name}"
        with zipfile.ZipFile(BytesIO(outer.read(inner_name))) as inner:
            # One wrapper level is the contract. If the inner archive itself has
            # no XML, return no members so the caller records an unsupported shape.
            yield from _xml_members_from_zip(inner, inner_source)


def _all_archive_names(package: dict[str, Any]) -> list[str]:
    with zipfile.ZipFile(package["path"]) as archive:
        return sorted(member for member in archive.namelist() if not member.endswith("/"))


def _directory_members(root: Path, package: dict[str, Any]) -> Iterator[tuple[str, bytes]]:
    candidates = sorted(
        (
            member
            for member in package["path"].rglob("*")
            if member.is_file() and member.suffix.lower() == ".xml"
        ),
        key=lambda member: member.as_posix(),
    )
    for member in candidates:
        yield member.relative_to(root).as_posix(), member.read_bytes()


def _all_directory_names(root: Path, package: dict[str, Any]) -> list[str]:
    del root
    return sorted(
        path.relative_to(package["path"]).as_posix()
        for path in package["path"].rglob("*")
        if path.is_file()
    )


def _content_element(root: ET.Element) -> ET.Element:
    content = [child for child in root if _local_name(child.tag) in CONTENT_KINDS]
    if len(content) != 1:
        raise ValueError("expected exactly one PAULA content element")
    return content[0]


def _header_id(root: ET.Element) -> str | None:
    for child in root:
        if _local_name(child.tag) == "header":
            return child.attrib.get("paula_id")
    return None


def _feature_values(content: ET.Element) -> list[str]:
    return [
        child.attrib["value"]
        for child in content
        if _local_name(child.tag) == "feat" and "value" in child.attrib
    ]


def _multi_feature_values(content: ET.Element) -> dict[str, list[str]]:
    output: dict[str, list[str]] = defaultdict(list)
    for multi_feature in content:
        if _local_name(multi_feature.tag) != "multiFeat":
            continue
        for feature in multi_feature:
            if (
                _local_name(feature.tag) == "feat"
                and feature.attrib.get("name")
                and "value" in feature.attrib
            ):
                output[feature.attrib["name"]].append(feature.attrib["value"])
    return {key: output[key] for key in sorted(output)}


def _is_metadata_base(base: str | None) -> bool:
    if not base:
        return False
    normalized = base.strip()
    basename = Path(normalized).name
    return normalized == "meta" or basename == "anno.xml" or basename.endswith(".anno.xml")


def audit_upstream(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    packages = _packages(root_path)
    packaging: Counter[str] = Counter()
    element_kinds: Counter[str] = Counter()
    list_types: dict[str, Counter[str]] = defaultdict(Counter)
    metadata_types: Counter[str] = Counter()
    metadata: list[dict[str, Any]] = []
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    errors: list[dict[str, str]] = []
    packages_without_xml: list[dict[str, Any]] = []
    xml_count = 0
    parsed = 0

    for package in packages:
        packaging[package["packaging"]] += 1
        try:
            members = (
                list(_archive_members(package))
                if package["packaging"] == "archive"
                else list(_directory_members(root_path, package))
            )
        except (OSError, zipfile.BadZipFile) as exc:
            errors.append(
                {"kind": "unreadable_package", "source": package["source"], "detail": str(exc)}
            )
            continue

        parsed += 1
        if not members:
            names = (
                _all_archive_names(package)
                if package["packaging"] == "archive"
                else _all_directory_names(root_path, package)
            )
            packages_without_xml.append(
                {
                    "dataset": package["dataset"],
                    "source": package["source"],
                    "members": names[:100],
                }
            )
            errors.append(
                {
                    "kind": "unsupported_package_shape",
                    "source": package["source"],
                    "detail": "no PAULA XML members",
                }
            )
            continue

        for source, raw in members:
            xml_count += 1
            try:
                xml_root = ET.fromstring(raw)
            except (ET.ParseError, UnicodeDecodeError) as exc:
                errors.append({"kind": "malformed_xml", "source": source, "detail": str(exc)})
                continue
            if _local_name(xml_root.tag) != "paula":
                errors.append(
                    {"kind": "invalid_root", "source": source, "detail": _local_name(xml_root.tag)}
                )
                continue
            try:
                content = _content_element(xml_root)
            except ValueError as exc:
                errors.append({"kind": "invalid_content", "source": source, "detail": str(exc)})
                continue

            kind = _local_name(content.tag)
            element_kinds[kind] += 1
            feature_type = content.attrib.get("type")
            base = content.attrib.get(XML_BASE) or content.attrib.get("xml:base")
            paula_id = _header_id(xml_root)

            if kind != "body" and feature_type:
                list_types[kind][feature_type] += 1
            if kind == "featList" and feature_type and len(examples[feature_type]) < 3:
                examples[feature_type].append(
                    {
                        "dataset": package["dataset"],
                        "source": source,
                        "paula_id": paula_id,
                        "base": base,
                        "values": _feature_values(content)[:5],
                    }
                )

            if (
                kind == "featList"
                and _is_metadata_base(base)
                and feature_type
                and feature_type != "annoFeat"
            ):
                metadata_types[feature_type] += 1
                metadata.append(
                    {
                        "dataset": package["dataset"],
                        "source": source,
                        "paula_id": paula_id,
                        "base": base,
                        "type": feature_type,
                        "values": _feature_values(content),
                    }
                )
            elif kind == "multiFeatList" and _is_metadata_base(base):
                for metadata_type, values in _multi_feature_values(content).items():
                    metadata_types[metadata_type] += 1
                    metadata.append(
                        {
                            "dataset": package["dataset"],
                            "source": source,
                            "paula_id": paula_id,
                            "base": base,
                            "type": metadata_type,
                            "values": values,
                        }
                    )

    return {
        "source_package_count": len(packages),
        "parsed_package_count": parsed,
        "datasets": [package["dataset"] for package in packages],
        "packaging": _ordered(packaging),
        "xml_member_count": xml_count,
        "element_kind_counts": _ordered(element_kinds),
        "list_type_occurrences": {
            key: _ordered(list_types[key]) for key in sorted(list_types)
        },
        "feature_type_examples": {key: examples[key] for key in sorted(examples)},
        "metadata_feature_type_occurrences": _ordered(metadata_types),
        "metadata_feature_instances": sorted(
            metadata,
            key=lambda item: (item["dataset"], item["source"], item["type"]),
        ),
        "packages_without_xml_members": sorted(
            packages_without_xml, key=lambda item: item["dataset"]
        ),
        "errors": sorted(
            errors,
            key=lambda item: (
                item.get("source", ""),
                item.get("kind", ""),
                item.get("detail", ""),
            ),
        ),
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
