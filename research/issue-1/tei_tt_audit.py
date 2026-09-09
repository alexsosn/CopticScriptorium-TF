"""Corpus-wide TEI ↔ TT source-coverage and layer-presence audit.

This research audit tests whether TEI exposes candidate semantic layers that are
absent from the corresponding source-native TT record. It deliberately compares
presence, not byte serialization or value normalization. Any TEI-only presence is
reported for targeted follow-up rather than treated as automatic parser authority.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any, Iterator
import xml.etree.ElementTree as ET
import zipfile


TEI_NS = "http://www.tei-c.org/ns/1.0"
LAYERS = ("column", "cts", "lemma", "license", "line", "page", "pos", "translation")
META_ATTR_RE = re.compile(r'\s+([A-Za-z_][A-Za-z0-9_.:-]*)\s*=\s*"([^"]*)"')
TT_LAYER_PATTERNS = {
    "lemma": re.compile(r"<norm\b[^>]*\blemma\s*="),
    "pos": re.compile(r"<norm\b[^>]*\bpos\s*="),
    "translation": re.compile(r"<translation\b"),
    "page": re.compile(r"<(?:pb|pb_[A-Za-z0-9_]+)\b"),
    "column": re.compile(r"<(?:cb|cb_[A-Za-z0-9_]+)\b"),
    "line": re.compile(r"<(?:lb|lb_[A-Za-z0-9_]+)\b"),
}


def _tei(tag: str) -> str:
    return f"{{{TEI_NS}}}{tag}"


def _first_meta_attrs(text: str) -> dict[str, str]:
    for line in text.splitlines():
        stripped = line.strip().lstrip("\ufeff")
        if not stripped:
            continue
        if not stripped.startswith("<meta"):
            return {}
        return {name: value for name, value in META_ATTR_RE.findall(stripped)}
    return {}


def _tt_layers(text: str) -> dict[str, bool]:
    attrs = _first_meta_attrs(text)
    flags = {layer: False for layer in LAYERS}
    flags["cts"] = bool(attrs.get("document_cts_urn"))
    flags["license"] = bool(attrs.get("license"))
    for layer, pattern in TT_LAYER_PATTERNS.items():
        flags[layer] = bool(pattern.search(text))
    return flags


def _tei_layers(root: ET.Element) -> dict[str, bool]:
    words = list(root.iter(_tei("w")))
    return {
        "cts": any((title.attrib.get("ref") or "").strip() for title in root.iter(_tei("title"))),
        "license": any(True for _ in root.iter(_tei("licence"))),
        "lemma": any((word.attrib.get("lemma") or "").strip() for word in words),
        "pos": any((word.attrib.get("type") or "").strip() for word in words),
        "translation": any((sentence.attrib.get("style") or "").strip() for sentence in root.iter(_tei("s"))),
        "page": any(True for _ in root.iter(_tei("pb"))),
        "column": any(True for _ in root.iter(_tei("cb"))),
        "line": any(True for _ in root.iter(_tei("lb"))),
    }


def _direct_tt_records(root: Path) -> Iterator[dict[str, Any]]:
    for directory in sorted(
        (path for path in root.rglob("*_TT") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        relative = directory.relative_to(root)
        if len(relative.parts) != 2 or not relative.parts[1].endswith("_TT"):
            continue
        corpus = relative.parts[0]
        dataset_name = relative.parts[1][:-3]
        dataset = f"{corpus}/{dataset_name}"
        for path in sorted(
            (
                item
                for item in directory.rglob("*")
                if item.is_file() and item.suffix.casefold() == ".tt"
            ),
            key=lambda item: item.as_posix(),
        ):
            relative_record = path.relative_to(directory).as_posix()
            record = relative_record[: -len(path.suffix)]
            yield {
                "dataset": dataset,
                "record": record,
                "source": path.relative_to(root).as_posix(),
                "packaging": "directory",
                "text": path.read_text(encoding="utf-8"),
            }


def _archive_tt_records(root: Path) -> Iterator[dict[str, Any]]:
    for archive_path in sorted(root.rglob("*_TT.zip"), key=lambda path: path.as_posix()):
        relative = archive_path.relative_to(root)
        if len(relative.parts) != 2 or not relative.parts[1].endswith("_TT.zip"):
            continue
        corpus = relative.parts[0]
        dataset_name = relative.parts[1][:-7]
        dataset = f"{corpus}/{dataset_name}"
        expected_prefix = f"{dataset_name}_TT/"
        with zipfile.ZipFile(archive_path) as archive:
            for member in sorted(archive.namelist()):
                if member.endswith("/") or not member.lower().endswith(".tt"):
                    continue
                logical = member
                if logical.startswith(expected_prefix):
                    logical = logical[len(expected_prefix):]
                elif "/" in logical:
                    first, rest = logical.split("/", 1)
                    if first.endswith("_TT"):
                        logical = rest
                record = logical[:-3]
                yield {
                    "dataset": dataset,
                    "record": record,
                    "source": f"{relative.as_posix()}!/{member}",
                    "packaging": "archive",
                    "text": archive.read(member).decode("utf-8"),
                }


def _tei_records(root: Path) -> Iterator[dict[str, Any]]:
    for directory in sorted(
        (path for path in root.rglob("*_TEI") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        relative = directory.relative_to(root)
        if len(relative.parts) != 2 or not relative.parts[1].endswith("_TEI"):
            continue
        corpus = relative.parts[0]
        dataset_name = relative.parts[1][:-4]
        dataset = f"{corpus}/{dataset_name}"
        for path in sorted(
            (
                item
                for item in directory.rglob("*")
                if item.is_file() and item.suffix.casefold() == ".xml"
            ),
            key=lambda item: item.as_posix(),
        ):
            relative_record = path.relative_to(directory).as_posix()
            record = relative_record[: -len(path.suffix)]
            yield {
                "dataset": dataset,
                "record": record,
                "source": path.relative_to(root).as_posix(),
                "path": path,
            }


def _index(records: Iterator[dict[str, Any]], representation: str) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["dataset"], record["record"].casefold())
        if key in indexed:
            previous = indexed[key]
            raise ValueError(
                f"case-insensitive {representation} record collision in {record['dataset']}: "
                f"{previous['record']!r} versus {record['record']!r}"
            )
        indexed[key] = record
    return indexed


def _ordered(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def audit_upstream(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    tt_records = list(_direct_tt_records(root_path)) + list(_archive_tt_records(root_path))
    tei_records = list(_tei_records(root_path))
    tt_index = _index(iter(tt_records), "TT")
    tei_index = _index(iter(tei_records), "TEI")

    tt_datasets = {record["dataset"] for record in tt_records}
    tei_datasets = {record["dataset"] for record in tei_records}
    tt_datasets_without_tei = sorted(tt_datasets - tei_datasets)

    tt_keys_in_tei_datasets = {
        key for key in tt_index if key[0] in tei_datasets
    }
    tei_keys = set(tei_index)
    paired_keys = sorted(tt_keys_in_tei_datasets & tei_keys)

    tt_only = [
        f"{dataset}:{tt_index[(dataset, key)]['record']}"
        for dataset, key in sorted(tt_keys_in_tei_datasets - tei_keys)
    ]
    tei_only = [
        f"{dataset}:{tei_index[(dataset, key)]['record']}"
        for dataset, key in sorted(tei_keys - set(tt_index))
    ]

    case_variants: list[dict[str, str]] = []
    tei_only_layers: Counter[str] = Counter({layer: 0 for layer in LAYERS})
    tei_only_examples: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for dataset, key in paired_keys:
        tt = tt_index[(dataset, key)]
        tei = tei_index[(dataset, key)]
        if tt["record"] != tei["record"]:
            case_variants.append(
                {
                    "dataset": dataset,
                    "tt_record": tt["record"],
                    "tei_record": tei["record"],
                }
            )

        tt_flags = _tt_layers(tt["text"])
        try:
            tei_root = ET.parse(tei["path"]).getroot()
        except (ET.ParseError, UnicodeDecodeError, OSError) as exc:
            errors.append(
                {
                    "kind": "malformed_tei",
                    "source": tei["source"],
                    "detail": str(exc),
                }
            )
            continue
        tei_flags = _tei_layers(tei_root)
        for layer in LAYERS:
            if tei_flags[layer] and not tt_flags[layer]:
                tei_only_layers[layer] += 1
                if sum(1 for example in tei_only_examples if example["layer"] == layer) < 20:
                    tei_only_examples.append(
                        {
                            "dataset": dataset,
                            "record": tei["record"],
                            "layer": layer,
                            "tt_source": tt["source"],
                            "tei_source": tei["source"],
                        }
                    )

    packaging = Counter(record["packaging"] for record in tt_records if record["dataset"] in tei_datasets)
    return {
        "tt_document_count": len(tt_records),
        "tei_document_count": len(tei_records),
        "tei_dataset_count": len(tei_datasets),
        "paired_document_count": len(paired_keys),
        "tt_packaging": _ordered(packaging),
        "tt_datasets_without_tei": tt_datasets_without_tei,
        "tt_only_records_in_tei_datasets": tt_only,
        "tei_only_records": tei_only,
        "case_variant_count": len(case_variants),
        "case_variants": sorted(case_variants, key=lambda item: (item["dataset"], item["tt_record"], item["tei_record"])),
        "tei_only_layer_presence": {layer: tei_only_layers[layer] for layer in LAYERS},
        "tei_only_examples": sorted(
            tei_only_examples,
            key=lambda item: (item["layer"], item["dataset"], item["record"]),
        ),
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
