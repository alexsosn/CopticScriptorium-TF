"""Cross-format parity audit for Coptic Scriptorium TT and CoNLL-U exports.

The audit pairs source records by dataset plus a case-insensitive technical basename,
while preserving literal names from both representations. It verifies that the
shared token stream and shared annotations agree before CoNLL-U-only enrichments are
considered safe to merge. No conflict is resolved by this tool.
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


ATTR_RE = re.compile(r'\s+([A-Za-z_][A-Za-z0-9_.:-]*)\s*=\s*"([^"]*)"')
NORM_TAG_RE = re.compile(r'<norm\b((?:[^">]|"[^"]*")*)>', re.DOTALL)
SHARED_FIELDS = ("func", "head", "lemma", "norm", "pos")


def _scan_attributes(fragment: str) -> dict[str, str]:
    position = 0
    attrs: dict[str, str] = {}
    while position < len(fragment):
        if fragment[position:].strip() == "":
            break
        match = ATTR_RE.match(fragment, position)
        if match is None:
            raise ValueError(f"malformed tag attributes near offset {position}")
        name = match.group(1)
        value = html.unescape(match.group(2))
        if name in attrs:
            raise ValueError(f"duplicate token attribute {name!r}")
        attrs[name] = value
        position = match.end()
    return attrs


def _tt_tokens(text: str) -> list[dict[str, Any]]:
    raw_tokens: list[dict[str, str]] = []
    id_to_position: dict[str, int] = {}

    for position, match in enumerate(NORM_TAG_RE.finditer(text), start=1):
        attrs = _scan_attributes(match.group(1))
        xml_id = attrs.get("xml:id")
        if xml_id:
            if xml_id in id_to_position:
                raise ValueError(f"duplicate TT token xml:id {xml_id!r}")
            id_to_position[xml_id] = position
        raw_tokens.append(attrs)

    tokens: list[dict[str, Any]] = []
    for attrs in raw_tokens:
        raw_head = attrs.get("head")
        if raw_head:
            target = raw_head[1:] if raw_head.startswith("#") else raw_head
            if target not in id_to_position:
                raise ValueError(f"unresolved TT dependency head {raw_head!r}")
            normalized_head: int | None = id_to_position[target]
        elif attrs.get("func") == "root":
            normalized_head = 0
        else:
            normalized_head = None

        tokens.append(
            {
                "norm": attrs.get("norm"),
                "lemma": attrs.get("lemma"),
                "pos": attrs.get("pos"),
                "func": attrs.get("func"),
                "head": normalized_head,
            }
        )
    return tokens


def _conllu_tokens(text: str) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    sentence_rows: list[tuple[int, list[str], int]] = []

    def flush_sentence() -> None:
        nonlocal sentence_rows
        if not sentence_rows:
            return

        start_position = len(tokens)
        local_to_absolute: dict[int, int] = {}
        for offset, (local_id, _columns, line_number) in enumerate(
            sentence_rows, start=1
        ):
            if local_id in local_to_absolute:
                raise ValueError(
                    f"duplicate CoNLL-U token id {local_id} at line {line_number}"
                )
            local_to_absolute[local_id] = start_position + offset

        for local_id, columns, line_number in sentence_rows:
            def value(column: str) -> str | None:
                return None if column == "_" else column

            raw_head = columns[6]
            if raw_head == "_":
                normalized_head: int | None = None
            else:
                try:
                    head_id = int(raw_head)
                except ValueError as exc:
                    raise ValueError(
                        f"invalid CoNLL-U HEAD {raw_head!r} at line {line_number}"
                    ) from exc
                if head_id == 0:
                    normalized_head = 0
                elif head_id in local_to_absolute:
                    normalized_head = local_to_absolute[head_id]
                else:
                    raise ValueError(
                        f"unresolved CoNLL-U HEAD {head_id} at line {line_number}"
                    )

            tokens.append(
                {
                    "norm": value(columns[1]),
                    "lemma": value(columns[2]),
                    "pos": value(columns[4]),
                    "func": value(columns[7]),
                    "head": normalized_head,
                }
            )
        sentence_rows = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            flush_sentence()
            continue
        if line.startswith("#"):
            continue
        columns = line.split("\t")
        if len(columns) != 10:
            raise ValueError(f"invalid CoNLL-U column count at line {line_number}")
        row_id = columns[0]
        if not row_id.isdigit():
            continue
        sentence_rows.append((int(row_id), columns, line_number))

    flush_sentence()
    return tokens


def _direct_tt_records(root: Path) -> Iterator[dict[str, Any]]:
    for directory in sorted(
        (path for path in root.rglob("*_TT") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        relative_dir = directory.relative_to(root)
        parts = relative_dir.parts
        if len(parts) != 2 or not parts[1].endswith("_TT"):
            continue
        corpus = parts[0]
        dataset_name = parts[1][:-3]
        dataset = f"{corpus}/{dataset_name}"
        for path in sorted(directory.rglob("*.tt"), key=lambda item: item.as_posix()):
            relative_record = path.relative_to(directory).as_posix()
            record = relative_record[:-3]
            yield {
                "dataset": dataset,
                "record": record,
                "source": path.relative_to(root).as_posix(),
                "packaging": "directory",
                "text": path.read_text(encoding="utf-8", errors="replace"),
            }


def _archive_tt_records(root: Path) -> Iterator[dict[str, Any]]:
    for archive_path in sorted(root.rglob("*_TT.zip"), key=lambda path: path.as_posix()):
        relative = archive_path.relative_to(root)
        parts = relative.parts
        if len(parts) != 2 or not parts[1].endswith("_TT.zip"):
            continue
        corpus = parts[0]
        dataset_name = parts[1][:-7]
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
                    "text": archive.read(member).decode("utf-8", errors="replace"),
                }


def _conllu_records(root: Path) -> Iterator[dict[str, Any]]:
    for directory in sorted(
        (path for path in root.rglob("*_CONLLU") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        relative_dir = directory.relative_to(root)
        parts = relative_dir.parts
        if len(parts) != 2 or not parts[1].endswith("_CONLLU"):
            continue
        corpus = parts[0]
        dataset_name = parts[1][:-7]
        dataset = f"{corpus}/{dataset_name}"
        for path in sorted(directory.rglob("*.conllu"), key=lambda item: item.as_posix()):
            relative_record = path.relative_to(directory).as_posix()
            record = relative_record[:-7]
            yield {
                "dataset": dataset,
                "record": record,
                "source": path.relative_to(root).as_posix(),
                "text": path.read_text(encoding="utf-8", errors="replace"),
            }


def _index(
    records: Iterator[dict[str, Any]], representation: str
) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["dataset"], record["record"].casefold())
        if key in indexed:
            previous = indexed[key]
            raise ValueError(
                "case-insensitive record collision in "
                f"{representation} dataset {record['dataset']}: "
                f"{previous['record']!r} versus {record['record']!r}"
            )
        indexed[key] = record
    return indexed


def audit_upstream(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    tt_records = list(_direct_tt_records(root_path)) + list(_archive_tt_records(root_path))
    conllu_records = list(_conllu_records(root_path))
    tt_index = _index(iter(tt_records), "TT")
    conllu_index = _index(iter(conllu_records), "CoNLL-U")

    tt_keys = set(tt_index)
    conllu_keys = set(conllu_index)
    paired_keys = sorted(tt_keys & conllu_keys)

    tt_only = [
        f"{dataset}:{tt_index[(dataset, key)]['record']}"
        for dataset, key in sorted(tt_keys - conllu_keys)
    ]
    conllu_only = [
        f"{dataset}:{conllu_index[(dataset, key)]['record']}"
        for dataset, key in sorted(conllu_keys - tt_keys)
    ]

    packaging: Counter[str] = Counter(record["packaging"] for record in tt_records)
    case_variants: list[dict[str, str]] = []
    conllu_placeholders: list[dict[str, str]] = []
    token_count_mismatches: list[dict[str, Any]] = []
    mismatch_counts: Counter[str] = Counter({field: 0 for field in SHARED_FIELDS})
    mismatch_examples: list[dict[str, Any]] = []
    compared_document_count = 0
    compared_tokens = 0

    for dataset, key in paired_keys:
        tt = tt_index[(dataset, key)]
        conllu = conllu_index[(dataset, key)]
        if tt["record"] != conllu["record"]:
            case_variants.append(
                {
                    "dataset": dataset,
                    "tt_record": tt["record"],
                    "conllu_record": conllu["record"],
                }
            )

        if not conllu["text"].strip():
            conllu_placeholders.append(
                {
                    "dataset": dataset,
                    "record": conllu["record"],
                    "source": conllu["source"],
                }
            )
            continue

        try:
            tt_tokens = _tt_tokens(tt["text"])
            conllu_tokens = _conllu_tokens(conllu["text"])
        except ValueError as exc:
            token_count_mismatches.append(
                {
                    "dataset": dataset,
                    "record": tt["record"],
                    "tt_tokens": None,
                    "conllu_tokens": None,
                    "error": str(exc),
                }
            )
            continue

        if len(tt_tokens) != len(conllu_tokens):
            token_count_mismatches.append(
                {
                    "dataset": dataset,
                    "record": tt["record"],
                    "tt_tokens": len(tt_tokens),
                    "conllu_tokens": len(conllu_tokens),
                }
            )
            continue

        compared_document_count += 1
        compared_tokens += len(tt_tokens)
        for token_index, (tt_token, conllu_token) in enumerate(
            zip(tt_tokens, conllu_tokens, strict=True), start=1
        ):
            for field in SHARED_FIELDS:
                if tt_token[field] == conllu_token[field]:
                    continue
                mismatch_counts[field] += 1
                if len(mismatch_examples) < 100:
                    mismatch_examples.append(
                        {
                            "dataset": dataset,
                            "record": tt["record"],
                            "token_index": token_index,
                            "field": field,
                            "tt": tt_token[field],
                            "conllu": conllu_token[field],
                        }
                    )

    conllu_placeholders = sorted(
        conllu_placeholders,
        key=lambda item: (item["dataset"], item["record"], item["source"]),
    )
    return {
        "tt_document_count": len(tt_records),
        "conllu_document_count": len(conllu_records),
        "paired_document_count": len(paired_keys),
        "compared_document_count": compared_document_count,
        "conllu_placeholder_count": len(conllu_placeholders),
        "conllu_placeholders": conllu_placeholders,
        "tt_packaging": {key: packaging[key] for key in sorted(packaging)},
        "tt_only": tt_only,
        "conllu_only": conllu_only,
        "case_variant_pairs": sorted(
            case_variants,
            key=lambda item: (item["dataset"], item["tt_record"], item["conllu_record"]),
        ),
        "token_count_mismatches": sorted(
            token_count_mismatches,
            key=lambda item: (item["dataset"], item["record"]),
        ),
        "compared_tokens": compared_tokens,
        "field_mismatch_counts": {
            field: mismatch_counts[field] for field in sorted(SHARED_FIELDS)
        },
        "field_mismatch_examples": mismatch_examples,
    }


def render_report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "upstream", type=Path, help="Pinned CopticScriptorium/corpora checkout"
    )
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
