"""Corpus-wide relANNIS metadata reconciliation for Coptic Scriptorium.

The repository README identifies PAULA/relANNIS as the representations carrying
corpus-level metadata. This research audit reads only the relANNIS corpus tables
needed for that question, keeps corpus-node metadata separate from document
metadata, and compares document annotations with the global ``meta.json`` index
without choosing merge precedence.

Directory-packaged ANNIS 3 tables (``*.annis``) and archive-packaged legacy
relANNIS tables (``*.tab``) are supported. Some upstream ``*_ANNIS.zip`` packages
contain only ANNIS configuration/viewer assets and no corpus metadata tables; those
packages are recorded explicitly as metadata-unavailable rather than silently
ignored. relANNIS files use PostgreSQL COPY text escaping, which is decoded before
comparison.
"""

from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
from typing import Any, Iterator
import zipfile


MAX_EXAMPLES = 100
CONFIG_ONLY_SIGNATURE = frozenset({"annis.version", "resolver_vis_map.annis"})


def _ordered(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _pg_unescape(value: str) -> str | None:
    """Decode PostgreSQL COPY text backslash escapes used by relANNIS."""

    if value == r"\N":
        return None

    simple = {
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
        "\\": "\\",
    }
    out: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\" or index + 1 >= len(value):
            out.append(char)
            index += 1
            continue

        escaped = value[index + 1]
        if escaped in simple:
            out.append(simple[escaped])
            index += 2
            continue

        if escaped in "01234567":
            end = index + 1
            while end < len(value) and end < index + 4 and value[end] in "01234567":
                end += 1
            out.append(chr(int(value[index + 1 : end], 8)))
            index = end
            continue

        if escaped == "x":
            end = index + 2
            while (
                end < len(value)
                and end < index + 4
                and value[end] in "0123456789abcdefABCDEF"
            ):
                end += 1
            if end > index + 2:
                out.append(chr(int(value[index + 2 : end], 16)))
                index = end
                continue

        out.append(escaped)
        index += 2

    return "".join(out)


def _split_row(
    line: str, expected: int, source: str, line_number: int
) -> list[str | None]:
    columns = line.split("\t")
    if len(columns) != expected:
        raise ValueError(
            f"invalid relANNIS column count in {source} line {line_number}: "
            f"expected {expected}, got {len(columns)}"
        )
    return [_pg_unescape(column) for column in columns]


def _direct_datasets(root: Path) -> Iterator[dict[str, str]]:
    for directory in sorted(
        (path for path in root.rglob("*_ANNIS") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        relative = directory.relative_to(root)
        if len(relative.parts) != 2:
            continue
        corpus = relative.parts[0]
        dataset_name = relative.parts[1][:-6]
        corpus_path = directory / "corpus.annis"
        annotation_path = directory / "corpus_annotation.annis"
        if not corpus_path.is_file() or not annotation_path.is_file():
            missing = [
                name
                for name, path in (
                    ("corpus.annis", corpus_path),
                    ("corpus_annotation.annis", annotation_path),
                )
                if not path.is_file()
            ]
            raise ValueError(
                f"relANNIS dataset {relative.as_posix()} missing required file(s): "
                + ", ".join(missing)
            )
        yield {
            "dataset": f"{corpus}/{dataset_name}",
            "packaging": "directory",
            "corpus_source": corpus_path.relative_to(root).as_posix(),
            "annotation_source": annotation_path.relative_to(root).as_posix(),
            "corpus_text": corpus_path.read_text(encoding="utf-8"),
            "annotation_text": annotation_path.read_text(encoding="utf-8"),
        }


def _archive_basenames(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        {
            Path(name).name
            for name in archive.namelist()
            if not name.endswith("/")
        }
    )


def _archive_members_by_basename(
    archive: zipfile.ZipFile, basename: str
) -> list[str]:
    return sorted(
        name
        for name in archive.namelist()
        if not name.endswith("/") and Path(name).name == basename
    )


def _archive_table_pair(
    archive: zipfile.ZipFile, source: str
) -> tuple[str, str] | None:
    candidates: list[tuple[str, str, str]] = []
    incomplete: list[str] = []
    for label, corpus_name, annotation_name in (
        ("annis", "corpus.annis", "corpus_annotation.annis"),
        ("tab", "corpus.tab", "corpus_annotation.tab"),
    ):
        corpus_members = _archive_members_by_basename(archive, corpus_name)
        annotation_members = _archive_members_by_basename(archive, annotation_name)
        if len(corpus_members) > 1 or len(annotation_members) > 1:
            raise ValueError(
                f"relANNIS archive {source} has duplicate {label} metadata tables"
            )
        if corpus_members and annotation_members:
            candidates.append((label, corpus_members[0], annotation_members[0]))
        elif corpus_members or annotation_members:
            incomplete.append(label)

    if incomplete:
        raise ValueError(
            f"relANNIS archive {source} has incomplete metadata table pair(s): "
            + ", ".join(sorted(incomplete))
        )
    if len(candidates) > 1:
        layouts = ", ".join(candidate[0] for candidate in candidates)
        raise ValueError(
            f"relANNIS archive {source} expected exactly one metadata table layout; "
            f"found {layouts}"
        )
    if not candidates:
        basenames = _archive_basenames(archive)
        if CONFIG_ONLY_SIGNATURE <= set(basenames):
            return None
        available = ", ".join(basenames) or "<empty>"
        raise ValueError(
            f"relANNIS archive {source} expected exactly one metadata table layout; "
            f"found none; available basenames: {available}"
        )

    _label, corpus_member, annotation_member = candidates[0]
    return corpus_member, annotation_member


def _archive_datasets(
    root: Path,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    datasets: list[dict[str, str]] = []
    unavailable: list[dict[str, Any]] = []
    for archive_path in sorted(root.rglob("*_ANNIS.zip"), key=lambda path: path.as_posix()):
        relative = archive_path.relative_to(root)
        if len(relative.parts) != 2:
            continue
        corpus = relative.parts[0]
        dataset_name = relative.parts[1][:-10]
        dataset = f"{corpus}/{dataset_name}"
        source = relative.as_posix()
        with zipfile.ZipFile(archive_path) as archive:
            pair = _archive_table_pair(archive, source)
            if pair is None:
                unavailable.append(
                    {
                        "dataset": dataset,
                        "source": source,
                        "classification": "configuration_only",
                        "available_basenames": _archive_basenames(archive),
                    }
                )
                continue
            corpus_member, annotation_member = pair
            datasets.append(
                {
                    "dataset": dataset,
                    "packaging": "archive",
                    "corpus_source": f"{source}!/{corpus_member}",
                    "annotation_source": f"{source}!/{annotation_member}",
                    "corpus_text": archive.read(corpus_member).decode("utf-8"),
                    "annotation_text": archive.read(annotation_member).decode("utf-8"),
                }
            )
    return datasets, unavailable


def _datasets(
    root: Path,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    archive_datasets, unavailable = _archive_datasets(root)
    datasets = list(_direct_datasets(root)) + archive_datasets
    indexed: dict[str, dict[str, str]] = {}
    for dataset in datasets:
        key = dataset["dataset"]
        if key in indexed:
            raise ValueError(f"duplicate relANNIS dataset representation for {key}")
        indexed[key] = dataset

    unavailable_by_dataset: dict[str, dict[str, Any]] = {}
    for entry in unavailable:
        key = str(entry["dataset"])
        if key in indexed or key in unavailable_by_dataset:
            raise ValueError(f"duplicate relANNIS dataset representation for {key}")
        unavailable_by_dataset[key] = entry

    return (
        [indexed[key] for key in sorted(indexed)],
        [unavailable_by_dataset[key] for key in sorted(unavailable_by_dataset)],
    )


def _parse_corpus_table(dataset: dict[str, str]) -> dict[int, dict[str, Any]]:
    source = dataset["corpus_source"]
    nodes: dict[int, dict[str, Any]] = {}
    document_names: dict[str, str] = {}

    for line_number, line in enumerate(dataset["corpus_text"].splitlines(), start=1):
        if not line:
            continue
        columns = _split_row(line, 7, source, line_number)
        raw_id, name, node_type, version, pre, post, top_level = columns
        if raw_id is None or name is None or node_type is None:
            raise ValueError(
                f"NULL required relANNIS corpus field in {source} line {line_number}"
            )
        try:
            node_id = int(raw_id)
        except ValueError as exc:
            raise ValueError(
                f"invalid relANNIS corpus id {raw_id!r} in {source} line {line_number}"
            ) from exc
        if node_id in nodes:
            raise ValueError(f"duplicate relANNIS corpus id {node_id} in {source}")
        if node_type not in {"DOCUMENT", "CORPUS"}:
            raise ValueError(
                f"invalid relANNIS corpus type {node_type!r} in {source} line {line_number}"
            )
        if node_type == "DOCUMENT":
            technical = name.casefold()
            if technical in document_names:
                previous = document_names[technical]
                raise ValueError(
                    "relANNIS case-insensitive document collision in "
                    f"{dataset['dataset']}: {previous!r} versus {name!r}"
                )
            document_names[technical] = name
        nodes[node_id] = {
            "name": name,
            "type": node_type,
            "version": version,
            "pre": pre,
            "post": post,
            "top_level": top_level,
        }
    return nodes


def _annotation_key(
    namespace: str | None, name: str | None, source: str, line: int
) -> str:
    if name is None or not name:
        raise ValueError(f"missing relANNIS annotation name in {source} line {line}")
    if namespace in {None, "", "NULL"}:
        return name
    return f"{namespace}:{name}"


def _parse_annotations(
    dataset: dict[str, str], nodes: dict[int, dict[str, Any]]
) -> dict[int, dict[str, list[str | None]]]:
    source = dataset["annotation_source"]
    annotations: dict[int, dict[str, list[str | None]]] = {}
    for line_number, line in enumerate(dataset["annotation_text"].splitlines(), start=1):
        if not line:
            continue
        columns = _split_row(line, 4, source, line_number)
        raw_ref, namespace, raw_name, value = columns
        if raw_ref is None:
            raise ValueError(f"NULL relANNIS corpus_ref in {source} line {line_number}")
        try:
            corpus_ref = int(raw_ref)
        except ValueError as exc:
            raise ValueError(
                f"invalid relANNIS corpus_ref {raw_ref!r} in {source} line {line_number}"
            ) from exc
        if corpus_ref not in nodes:
            raise ValueError(
                f"dangling relANNIS corpus_ref {corpus_ref} in {source} line {line_number}"
            )
        key = _annotation_key(namespace, raw_name, source, line_number)
        annotations.setdefault(corpus_ref, {}).setdefault(key, []).append(value)
    return annotations


def _load_meta_json(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    path = root / "meta.json"
    if not path.is_file():
        raise ValueError("meta.json is missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("meta.json top level must be an object")

    technical_to_literal: dict[str, str] = {}
    for raw_key in value:
        literal = str(raw_key)
        technical = literal.casefold()
        if technical in technical_to_literal:
            previous = technical_to_literal[technical]
            raise ValueError(
                "meta.json case-insensitive key collision: "
                f"{previous!r} versus {literal!r}"
            )
        technical_to_literal[technical] = literal
    return value, technical_to_literal


def _unique_values(values: list[str | None]) -> list[str | None]:
    unique: list[str | None] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def audit_upstream(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    meta, meta_index = _load_meta_json(root_path)
    datasets, metadata_unavailable_archives = _datasets(root_path)

    packaging: Counter[str] = Counter()
    document_count = 0
    corpus_node_count = 0
    matched_count = 0
    used_meta_keys: set[str] = set()
    annis_without_meta: list[dict[str, str]] = []
    mismatch_counts: Counter[str] = Counter()
    annis_missing_in_meta: Counter[str] = Counter()
    meta_missing_in_annis: Counter[str] = Counter()
    document_keys: Counter[str] = Counter()
    corpus_keys: Counter[str] = Counter()
    mismatch_examples: list[dict[str, Any]] = []
    duplicate_equal_occurrences = 0
    duplicate_conflicting_occurrences = 0
    duplicate_conflict_examples: list[dict[str, Any]] = []
    corpus_annotations: list[dict[str, Any]] = []

    for dataset in datasets:
        packaging[dataset["packaging"]] += 1
        nodes = _parse_corpus_table(dataset)
        annotations = _parse_annotations(dataset, nodes)

        for node_id in sorted(nodes):
            node = nodes[node_id]
            node_annotations = annotations.get(node_id, {})
            if node["type"] == "CORPUS":
                corpus_node_count += 1
                for key, values in sorted(node_annotations.items()):
                    corpus_keys[key] += len(values)
                corpus_annotations.append(
                    {
                        "dataset": dataset["dataset"],
                        "corpus": node["name"],
                        "annotations": {
                            key: values for key, values in sorted(node_annotations.items())
                        },
                    }
                )
                continue

            document_count += 1
            for key, values in sorted(node_annotations.items()):
                document_keys[key] += len(values)
                if len(values) > 1:
                    unique = _unique_values(values)
                    if len(unique) == 1:
                        duplicate_equal_occurrences += len(values) - 1
                    else:
                        duplicate_conflicting_occurrences += 1
                        if len(duplicate_conflict_examples) < MAX_EXAMPLES:
                            duplicate_conflict_examples.append(
                                {
                                    "dataset": dataset["dataset"],
                                    "record": node["name"],
                                    "field": key,
                                    "values": values,
                                }
                            )

            technical = node["name"].casefold()
            literal_meta_key = meta_index.get(technical)
            if literal_meta_key is None:
                annis_without_meta.append(
                    {"dataset": dataset["dataset"], "record": node["name"]}
                )
                continue

            matched_count += 1
            used_meta_keys.add(literal_meta_key)
            meta_value = meta[literal_meta_key]
            if not isinstance(meta_value, dict):
                continue

            annis_fields = set(node_annotations)
            meta_fields = {str(key) for key in meta_value}
            for field in sorted(annis_fields - meta_fields):
                annis_missing_in_meta[field] += 1
            for field in sorted(meta_fields - annis_fields):
                meta_missing_in_annis[field] += 1

            for field in sorted(annis_fields & meta_fields):
                values = _unique_values(node_annotations[field])
                if len(values) != 1:
                    continue
                annis_value = values[0]
                json_value = meta_value[field]
                if isinstance(json_value, (dict, list)):
                    continue
                json_text = None if json_value is None else str(json_value)
                if annis_value == json_text:
                    continue
                mismatch_counts[field] += 1
                if len(mismatch_examples) < MAX_EXAMPLES:
                    mismatch_examples.append(
                        {
                            "dataset": dataset["dataset"],
                            "record": node["name"],
                            "field": field,
                            "annis": annis_value,
                            "meta_json": json_text,
                        }
                    )

    meta_without_annis = sorted(
        str(key) for key in meta if str(key) not in used_meta_keys
    )
    return {
        "source_package_count": len(datasets) + len(metadata_unavailable_archives),
        "dataset_count": len(datasets),
        "packaging": _ordered(packaging),
        "metadata_unavailable_archives": metadata_unavailable_archives,
        "document_count": document_count,
        "corpus_node_count": corpus_node_count,
        "matched_document_count": matched_count,
        "annis_documents_without_meta_json": sorted(
            annis_without_meta,
            key=lambda item: (item["dataset"], item["record"]),
        ),
        "meta_json_without_annis_document": meta_without_annis,
        "document_annotation_key_occurrences": _ordered(document_keys),
        "corpus_annotation_key_occurrences": _ordered(corpus_keys),
        "document_field_mismatch_counts": _ordered(mismatch_counts),
        "document_field_mismatch_examples": mismatch_examples,
        "annis_fields_missing_in_meta_counts": _ordered(annis_missing_in_meta),
        "meta_fields_missing_in_annis_counts": _ordered(meta_missing_in_annis),
        "duplicate_document_annotations": {
            "equal_value_extra_occurrences": duplicate_equal_occurrences,
            "conflicting_field_occurrences": duplicate_conflicting_occurrences,
            "conflict_examples": duplicate_conflict_examples,
        },
        "corpus_annotations": corpus_annotations,
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
