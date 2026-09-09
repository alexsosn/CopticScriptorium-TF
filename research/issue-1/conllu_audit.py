"""Corpus-wide feature census for Coptic Scriptorium CoNLL-U exports.

This research tool measures which annotations exist in CoNLL-U independently of
TreeTagger SGML, especially UD-normalized morphology and MISC enrichments such as
construction annotations. It also validates the sentence-local ID/dependency shape
needed for safe cross-format alignment. It does not choose merge precedence.
"""

from __future__ import annotations

from collections import Counter
import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


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


def _load_sibling(name: str, filename: str):
    module_path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load research module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ID_CONTRACT = _load_sibling("issue1_conllu_id_contract", "conllu_id_contract.py")
SOURCES = _load_sibling("issue1_conllu_sources", "conllu_sources.py")


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

    for record in SOURCES.iter_conllu_records(root_path):
        document_count += 1
        source = str(record["source"])
        seen_feats: set[str] = set()
        seen_misc: set[str] = set()
        file_token_rows = 0
        newdoc_ids: list[str] = []
        sentence_rows: list[tuple[int, str, int]] = []
        sentence_id_rows: list[dict[str, Any]] = []

        def flush_sentence() -> None:
            nonlocal sentence_rows, sentence_id_rows
            if not sentence_rows and not sentence_id_rows:
                return

            for issue in ID_CONTRACT.validate_sentence_id_rows(sentence_id_rows):
                errors.append(
                    {
                        "kind": issue["kind"],
                        "source": source,
                        "line": issue["line"],
                        "id": issue["id"],
                        "detail": issue["detail"],
                    }
                )

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
            sentence_id_rows = []

        text = str(record["text"])
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
            try:
                parsed_id = ID_CONTRACT.parse_row_id(row_id, line_number)
            except ID_CONTRACT.RowIdError as exc:
                errors.append(
                    {
                        "kind": exc.kind,
                        "source": source,
                        "line": exc.line,
                        "id": exc.raw_id,
                    }
                )
                continue

            if parsed_id["kind"] == "basic":
                token_id = int(parsed_id["first"])
                if any(existing_id == token_id for existing_id, _head, _line in sentence_rows):
                    errors.append(
                        {
                            "kind": "duplicate_token_id",
                            "source": source,
                            "line": line_number,
                            "id": row_id,
                        }
                    )
                    continue

                sentence_id_rows.append(parsed_id)
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
                continue

            sentence_id_rows.append(parsed_id)
            if parsed_id["kind"] == "multiword":
                multiword_rows += 1
                continue

            if parsed_id["kind"] == "empty":
                empty_node_rows += 1
                for key in _attribute_keys(row["FEATS"]):
                    feats_occurrences[key] += 1
                    seen_feats.add(key)
                for key in _attribute_keys(row["MISC"]):
                    misc_occurrences[key] += 1
                    seen_misc.add(key)
                continue

            raise AssertionError(f"unknown parsed CoNLL-U ID kind: {parsed_id['kind']}")

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
