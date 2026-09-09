"""Corpus-wide TEI shape and feature-presence audit for Coptic Scriptorium.

This research tool inventories TEI exports as evidence for source-authority
selection. It does not define or implement the production converter. The audit
records document identities, metadata/layer presence, layout boundaries inside
word markup, malformed XML, and case-insensitive identity collisions.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _tei(tag: str) -> str:
    return f"{{{TEI_NS}}}{tag}"


def _ordered(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _dataset_directories(root: Path) -> list[tuple[str, Path]]:
    datasets: list[tuple[str, Path]] = []
    for directory in sorted(
        (path for path in root.rglob("*_TEI") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        relative = directory.relative_to(root)
        parts = relative.parts
        if len(parts) != 2 or not parts[1].endswith("_TEI"):
            continue
        corpus = parts[0]
        dataset_name = parts[1][:-4]
        datasets.append((f"{corpus}/{dataset_name}", directory))
    return datasets


def _has(root: ET.Element, tag: str) -> bool:
    return root.find(f".//{_tei(tag)}") is not None


def _sentence_translation(root: ET.Element) -> bool:
    return any((element.attrib.get("style") or "").strip() for element in root.iter(_tei("s")))


def _word_split_by_layout(word: ET.Element) -> bool:
    return any(_local_name(element.tag) in {"pb", "cb", "lb"} for element in word.iter() if element is not word)


def audit_upstream(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    datasets = _dataset_directories(root_path)

    document_count = 0
    root_elements: Counter[str] = Counter()
    errors: list[dict[str, str]] = []
    records: dict[tuple[str, str], dict[str, str]] = {}

    documents_with_tei_header = 0
    documents_with_cts_ref = 0
    documents_with_license = 0
    documents_with_language_usage = 0
    documents_with_repository = 0
    documents_with_sentence_translation = 0
    documents_with_words = 0
    documents_with_morphemes = 0
    documents_with_page_breaks = 0
    documents_with_column_breaks = 0
    documents_with_line_breaks = 0
    words_split_by_layout = 0

    for dataset, directory in datasets:
        for path in sorted(directory.rglob("*.xml"), key=lambda item: item.as_posix()):
            relative_record = path.relative_to(directory).as_posix()
            record = relative_record[:-4]
            key = (dataset, record.casefold())
            if key in records:
                previous = records[key]
                raise ValueError(
                    "case-insensitive TEI record collision in "
                    f"{dataset}: {previous['record']!r} versus {record!r}"
                )
            source = path.relative_to(root_path).as_posix()
            records[key] = {"dataset": dataset, "record": record, "source": source}
            document_count += 1

            try:
                xml_root = ET.parse(path).getroot()
            except (ET.ParseError, UnicodeDecodeError, OSError) as exc:
                errors.append({"kind": "malformed_xml", "source": source, "detail": str(exc)})
                continue

            root_elements[_local_name(xml_root.tag)] += 1
            if _has(xml_root, "teiHeader"):
                documents_with_tei_header += 1
            if any((title.attrib.get("ref") or "").strip() for title in xml_root.iter(_tei("title"))):
                documents_with_cts_ref += 1
            if _has(xml_root, "licence"):
                documents_with_license += 1
            if _has(xml_root, "langUsage"):
                documents_with_language_usage += 1
            if _has(xml_root, "repository"):
                documents_with_repository += 1
            if _sentence_translation(xml_root):
                documents_with_sentence_translation += 1

            words = list(xml_root.iter(_tei("w")))
            if words:
                documents_with_words += 1
            if _has(xml_root, "m"):
                documents_with_morphemes += 1
            if _has(xml_root, "pb"):
                documents_with_page_breaks += 1
            if _has(xml_root, "cb"):
                documents_with_column_breaks += 1
            if _has(xml_root, "lb"):
                documents_with_line_breaks += 1
            words_split_by_layout += sum(1 for word in words if _word_split_by_layout(word))

    return {
        "dataset_count": len(datasets),
        "document_count": document_count,
        "datasets": [dataset for dataset, _directory in datasets],
        "root_element_counts": _ordered(root_elements),
        "documents_with_tei_header": documents_with_tei_header,
        "documents_with_cts_ref": documents_with_cts_ref,
        "documents_with_license": documents_with_license,
        "documents_with_language_usage": documents_with_language_usage,
        "documents_with_repository": documents_with_repository,
        "documents_with_sentence_translation": documents_with_sentence_translation,
        "documents_with_words": documents_with_words,
        "documents_with_morphemes": documents_with_morphemes,
        "documents_with_page_breaks": documents_with_page_breaks,
        "documents_with_column_breaks": documents_with_column_breaks,
        "documents_with_line_breaks": documents_with_line_breaks,
        "words_split_by_layout": words_split_by_layout,
        "records": [records[key] for key in sorted(records)],
        "errors": sorted(errors, key=lambda error: (error["source"], error["kind"], error["detail"])),
    }


def render_report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path, help="Pinned CopticScriptorium checkout")
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
