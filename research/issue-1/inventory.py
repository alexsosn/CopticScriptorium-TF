"""Pure inventory analysis for Coptic Scriptorium issue #1.

This module intentionally performs no network access. It consumes a Git Trees API
payload (or an equivalent JSON object produced from a local checkout) and returns a
deterministically ordered report. Network/download concerns belong to a separate
transport layer so the coverage logic can be tested independently.
"""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any


FORMAT_SUFFIXES = ("ANNIS", "CONLLU", "PAULA", "TEI", "TT")
RECORD_EXTENSIONS = {
    "CONLLU": ".conllu",
    "TEI": ".xml",
    "TT": ".tt",
}


def classify_format_directory(path: str) -> tuple[str, str, str] | None:
    """Classify a canonical top-level ``corpus/dataset_FORMAT`` directory."""

    parts = PurePosixPath(path).parts
    if len(parts) != 2:
        return None

    corpus, dirname = parts
    for fmt in FORMAT_SUFFIXES:
        suffix = f"_{fmt}"
        if dirname.endswith(suffix) and len(dirname) > len(suffix):
            return corpus, dirname[: -len(suffix)], fmt
    return None


def classify_format_archive(path: str) -> tuple[str, str, str] | None:
    """Classify a canonical top-level ``corpus/dataset_FORMAT.zip`` archive."""

    parts = PurePosixPath(path).parts
    if len(parts) != 2:
        return None

    corpus, filename = parts
    for fmt in FORMAT_SUFFIXES:
        suffix = f"_{fmt}.zip"
        if filename.endswith(suffix) and len(filename) > len(suffix):
            return corpus, filename[: -len(suffix)], fmt
    return None


def _new_dataset() -> dict[str, Any]:
    return {
        "formats": set(),
        "format_directories": {},
        "format_artifacts": {},
        "blob_counts": {},
        "records": {},
        "unexpected_files": [],
    }


def _record_identity(
    path: str,
    format_directories: dict[str, tuple[str, str]],
) -> tuple[str, str, str] | None:
    """Return ``(dataset_key, format, record_id)`` for visible record exports."""

    for directory, (dataset_key, fmt) in format_directories.items():
        extension = RECORD_EXTENSIONS.get(fmt)
        if extension is None:
            continue

        prefix = f"{directory}/"
        if not path.startswith(prefix) or not path.endswith(extension):
            continue

        relative = path[len(prefix) :]
        if not relative or relative.endswith("/"):
            return None
        record_id = relative[: -len(extension)]
        if not record_id:
            return None
        return dataset_key, fmt, record_id
    return None


def analyze_tree(payload: dict[str, Any]) -> dict[str, Any]:
    """Analyze one complete assembled Git tree payload.

    A truncated response is rejected. Format presence is kept separate from record
    visibility: some upstream corpora package TT/PAULA/ANNIS as opaque ZIP blobs,
    so their records cannot be called missing merely because the Git tree cannot see
    archive members.
    """

    if payload.get("truncated"):
        raise ValueError("cannot inventory a truncated Git tree response")

    entries = payload.get("tree")
    if not isinstance(entries, list):
        raise ValueError("tree payload must contain a list in 'tree'")

    sorted_entries = sorted(entries, key=lambda item: str(item.get("path", "")))

    top_level_corpora: list[str] = []
    zero_byte_blobs: list[dict[str, str]] = []
    meta_json: dict[str, Any] | None = None

    datasets: dict[str, dict[str, Any]] = {}
    format_directories: dict[str, tuple[str, str]] = {}

    for entry in sorted_entries:
        path = entry.get("path")
        entry_type = entry.get("type")
        if not isinstance(path, str):
            continue

        if entry_type == "tree" and "/" not in path:
            top_level_corpora.append(path)

        if entry_type == "tree":
            classified = classify_format_directory(path)
            if classified is not None:
                corpus, dataset_name, fmt = classified
                dataset_key = f"{corpus}/{dataset_name}"
                format_directories[path] = (dataset_key, fmt)
                dataset = datasets.setdefault(dataset_key, _new_dataset())
                dataset["formats"].add(fmt)
                dataset["format_directories"][fmt] = path
                dataset["format_artifacts"].setdefault(fmt, []).append(
                    {
                        "kind": "directory",
                        "path": path,
                        "sha": str(entry.get("sha", "")),
                    }
                )
                dataset["blob_counts"].setdefault(fmt, 0)

        if entry_type == "blob":
            archived = classify_format_archive(path)
            if archived is not None:
                corpus, dataset_name, fmt = archived
                dataset_key = f"{corpus}/{dataset_name}"
                dataset = datasets.setdefault(dataset_key, _new_dataset())
                dataset["formats"].add(fmt)
                dataset["format_artifacts"].setdefault(fmt, []).append(
                    {
                        "kind": "archive",
                        "path": path,
                        "sha": str(entry.get("sha", "")),
                        "size": int(entry.get("size", 0)),
                    }
                )
                dataset["blob_counts"][fmt] = dataset["blob_counts"].get(fmt, 0) + 1

            if entry.get("size") == 0:
                zero_byte_blobs.append(
                    {"path": path, "sha": str(entry.get("sha", ""))}
                )

            if path == "meta.json":
                meta_json = {
                    "path": path,
                    "sha": str(entry.get("sha", "")),
                    "size": int(entry.get("size", 0)),
                }

    # Count files beneath visible format directories and collect record-oriented
    # counterparts. PAULA and ANNIS are deliberately excluded from basename-level
    # record matching: their observed exports are component/corpus-oriented rather
    # than uniformly one-file-per-document.
    directories_longest_first = dict(
        sorted(format_directories.items(), key=lambda item: (-len(item[0]), item[0]))
    )

    for entry in sorted_entries:
        if entry.get("type") != "blob":
            continue
        path = entry.get("path")
        if not isinstance(path, str):
            continue

        containing: tuple[str, str] | None = None
        for directory, value in directories_longest_first.items():
            if path.startswith(f"{directory}/"):
                containing = value
                break

        if containing is not None:
            dataset_key, fmt = containing
            dataset = datasets[dataset_key]
            dataset["blob_counts"][fmt] = dataset["blob_counts"].get(fmt, 0) + 1

            expected_extension = RECORD_EXTENSIONS.get(fmt)
            if expected_extension is not None and not path.endswith(expected_extension):
                dataset["unexpected_files"].append(path)

        record = _record_identity(path, directories_longest_first)
        if record is None:
            continue
        dataset_key, fmt, record_id = record
        record_map = datasets[dataset_key]["records"].setdefault(record_id, {})
        if fmt in record_map:
            raise ValueError(
                f"duplicate {fmt} record identity {record_id!r} in dataset {dataset_key}"
            )
        record_map[fmt] = path

    final_datasets: dict[str, dict[str, Any]] = {}

    for dataset_key in sorted(datasets):
        raw = datasets[dataset_key]
        records: dict[str, dict[str, str]] = {}
        missing_counterparts: dict[str, list[str]] = {}

        archive_formats = {
            fmt
            for fmt, artifacts in raw["format_artifacts"].items()
            if any(artifact["kind"] == "archive" for artifact in artifacts)
        }
        visible_record_formats = sorted(
            fmt for fmt in RECORD_EXTENSIONS if fmt in raw["format_directories"]
        )
        record_comparison_coverage: dict[str, str] = {}
        for fmt in sorted(RECORD_EXTENSIONS):
            if fmt in raw["format_directories"]:
                record_comparison_coverage[fmt] = "visible"
            elif fmt in archive_formats:
                record_comparison_coverage[fmt] = "archive"
            else:
                record_comparison_coverage[fmt] = "absent"

        for record_id in sorted(raw["records"]):
            mapping = raw["records"][record_id]
            ordered_mapping = {fmt: mapping[fmt] for fmt in sorted(mapping)}
            records[record_id] = ordered_mapping
            missing = [fmt for fmt in visible_record_formats if fmt not in mapping]
            if missing:
                missing_counterparts[record_id] = missing

        ordered_artifacts: dict[str, list[dict[str, Any]]] = {}
        for fmt in sorted(raw["format_artifacts"]):
            ordered_artifacts[fmt] = sorted(
                raw["format_artifacts"][fmt],
                key=lambda artifact: (artifact["kind"], artifact["path"]),
            )

        final_datasets[dataset_key] = {
            "formats": sorted(raw["formats"]),
            "format_directories": {
                fmt: raw["format_directories"][fmt]
                for fmt in sorted(raw["format_directories"])
            },
            "format_artifacts": ordered_artifacts,
            "blob_counts": {
                fmt: raw["blob_counts"][fmt] for fmt in sorted(raw["blob_counts"])
            },
            "record_comparison_coverage": record_comparison_coverage,
            "records": records,
            "missing_counterparts": missing_counterparts,
            "unexpected_files": sorted(raw["unexpected_files"]),
        }

    return {
        "tree_sha": str(payload.get("sha", "")),
        "tree_complete": True,
        "top_level_corpora": sorted(set(top_level_corpora)),
        "meta_json": meta_json,
        "zero_byte_blobs": sorted(
            zero_byte_blobs, key=lambda item: (item["path"], item["sha"])
        ),
        "datasets": final_datasets,
    }


def render_report_json(report: dict[str, Any]) -> str:
    """Serialize a report reproducibly for version control and diffing."""

    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
