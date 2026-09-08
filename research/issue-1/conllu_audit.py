"""Corpus-wide feature census for Coptic Scriptorium CoNLL-U exports.

This research tool measures which annotations exist in CoNLL-U independently of
TreeTagger SGML, especially UD-normalized morphology and MISC enrichments such as
construction annotations. It also validates the basic sentence-local dependency
shape needed for safe cross-format alignment. It does not choose merge precedence.
"""

from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
from typing import Any, Iterator


COLUMN_NAMES = (
    "ID",
    "FORM",
    "LEMMA",
    "UPOS",
    "XPOS",
    "FEATS",
    "HEAD",
    "DEPREL",
    "DEPS",
    "MISC",
)


def _iter_conllu_files(root: Path) -> Iterator[Path]:
    directories = sorted(
        (path for path in root.rglob("*_CONLLU") if path.is_dir()),
        key=lambda path: path.as_posix(),
    )
    for directory in directories:
        yield from sorted(directory.rglob("*.conllu"), key=lambda path: path.as_posix())


def _attribute_keys(field: str) -> list[str]:
    if not field or field == "_":
        return []
    keys: list[str] = []
    for item in field.split("|"):
        item = item.strip()
        if not item:
            continue
        key = item.split("=", 1)[0]
        if key:
            keys.append(key)
    return keys


def _ordered(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def audit_upstream(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    document_count = 0
    token_rows = 0
    multiword_rows = 0
    empty_node_rows = 0
    enhanced_deps_rows = 0

    upos: Counter[str] = Counter()
    xpos: Counter[str] = Counter()
    feats_occurrences: Counter[str] = Counter()
    misc_occurrences: Counter[str] = Counter()
    feats_documents: Counter[str] = Counter()
    misc_documents: Counter[str] = Counter()
    comments: Counter[str] = Counter()
    errors: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []

    for path in _iter_conllu_files(root_path):
        document_count += 1
        source = path.relative_to(root_path).as_posix()
        seen_feats: set[str] = set()
        seen_misc: set[str] = set()
        file_token_rows = 0
        newdoc_ids: list[str] = []
        sentence_rows: list[tuple[int, str, int]] = []

        def flush_sentence() -> None:
            nonlocal sentence_rows
            if not sentence_rows:
                return
            ids = {token_id for token_id, _head, _line in sentence_rows}
            for _token_id, head, line_number in sentence_rows:
                if head == "_":
                    continue
                try:
                    head_id = int(head)
                except ValueError:
                    errors.append(
                        {
                            "kind": "invalid_head",
                            "source": source,
                            "line": line_number,
                            "head": head,
                        }
                    )
                    continue
                if head_id < 0:
                    errors.append(
                        {
                            "kind": "invalid_head",
                            "source": source,
                            "line": line_number,
                            "head": head,
                        }
                    )
                elif head_id > 0 and head_id not in ids:
                    errors.append(
                        {
                            "kind": "dangling_head",
                            "source": source,
                            "line": line_number,
                            "head": head,
                        }
                    )
            sentence_rows = []

        text = path.read_text(encoding="utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line:
                flush_sentence()
                continue
            if line.startswith("#"):
                content = line[1:].strip()
                if "=" in content:
                    key, value = content.split("=", 1)
                    key = key.strip()
                    if key:
                        comments[key] += 1
                        if key == "newdoc id":
                            newdoc_ids.append(value.strip())
                continue

            columns = line.split("\t")
            if len(columns) != 10:
                errors.append(
                    {
                        "kind": "invalid_column_count",
                        "source": source,
                        "line": line_number,
                        "columns": len(columns),
                    }
                )
                continue

            row = dict(zip(COLUMN_NAMES, columns, strict=True))
            row_id = row["ID"]
            if row_id.isdigit():
                token_id = int(row_id)
                if token_id <= 0:
                    errors.append(
                        {
                            "kind": "invalid_token_id",
                            "source": source,
                            "line": line_number,
                            "id": row_id,
                        }
                    )
                    continue

                token_rows += 1
                file_token_rows += 1
                sentence_rows.append((token_id, row["HEAD"], line_number))
                if row["UPOS"] != "_":
                    upos[row["UPOS"]] += 1
                if row["XPOS"] != "_":
                    xpos[row["XPOS"]] += 1

                for key in _attribute_keys(row["FEATS"]):
                    feats_occurrences[key] += 1
                    seen_feats.add(key)
                for key in _attribute_keys(row["MISC"]):
                    misc_occurrences[key] += 1
                    seen_misc.add(key)
                if row["DEPS"] != "_":
                    enhanced_deps_rows += 1
            elif "-" in row_id:
                multiword_rows += 1
            elif "." in row_id:
                empty_node_rows += 1
                for key in _attribute_keys(row["FEATS"]):
                    feats_occurrences[key] += 1
                    seen_feats.add(key)
                for key in _attribute_keys(row["MISC"]):
                    misc_occurrences[key] += 1
                    seen_misc.add(key)
            else:
                errors.append(
                    {
                        "kind": "invalid_id",
                        "source": source,
                        "line": line_number,
                        "id": row_id,
                    }
                )

        flush_sentence()
        for key in seen_feats:
            feats_documents[key] += 1
        for key in seen_misc:
            misc_documents[key] += 1
        documents.append(
            {
                "source": source,
                "token_rows": file_token_rows,
                "newdoc_ids": newdoc_ids,
            }
        )

    return {
        "document_count": document_count,
        "token_rows": token_rows,
        "multiword_rows": multiword_rows,
        "empty_node_rows": empty_node_rows,
        "enhanced_deps_rows": enhanced_deps_rows,
        "upos_values": _ordered(upos),
        "xpos_values": _ordered(xpos),
        "feats_key_occurrences": _ordered(feats_occurrences),
        "feats_key_documents": _ordered(feats_documents),
        "misc_key_occurrences": _ordered(misc_occurrences),
        "misc_key_documents": _ordered(misc_documents),
        "comment_key_occurrences": _ordered(comments),
        "errors": sorted(
            errors,
            key=lambda error: (
                error.get("source", ""),
                int(error.get("line", 0)),
                error.get("kind", ""),
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
