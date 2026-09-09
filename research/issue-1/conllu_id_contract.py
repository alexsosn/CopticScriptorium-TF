"""Shared CoNLL-U row-ID grammar and sentence-level structural validation.

The research audits use this module to keep the standalone CoNLL-U census and the
TT↔CoNLL-U parity gate on one validity contract.  It intentionally focuses on ID
structure needed for safe basic-token/head alignment; field-level UD semantics are
measured separately by the callers.
"""

from __future__ import annotations

import re
from typing import Any


BASIC_ID_RE = re.compile(r"[1-9][0-9]*")
MULTIWORD_ID_RE = re.compile(r"([1-9][0-9]*)-([1-9][0-9]*)")
# CoNLL-U permits sentence-initial empty nodes 0.1, 0.2, ... .
EMPTY_NODE_ID_RE = re.compile(r"(0|[1-9][0-9]*)\.([1-9][0-9]*)")


class RowIdError(ValueError):
    def __init__(self, kind: str, raw_id: str, line: int, message: str):
        super().__init__(message)
        self.kind = kind
        self.raw_id = raw_id
        self.line = line


def parse_row_id(raw_id: str, line: int) -> dict[str, Any]:
    """Parse one CoNLL-U ID and reject intrinsically invalid forms."""

    if BASIC_ID_RE.fullmatch(raw_id):
        return {"kind": "basic", "raw": raw_id, "line": line, "first": int(raw_id)}

    multiword = MULTIWORD_ID_RE.fullmatch(raw_id)
    if multiword is not None:
        start, end = (int(value) for value in multiword.groups())
        if start >= end:
            raise RowIdError(
                "invalid_id",
                raw_id,
                line,
                f"invalid CoNLL-U multiword range {raw_id!r} at line {line}",
            )
        return {
            "kind": "multiword",
            "raw": raw_id,
            "line": line,
            "first": start,
            "second": end,
        }

    empty = EMPTY_NODE_ID_RE.fullmatch(raw_id)
    if empty is not None:
        base, suffix = (int(value) for value in empty.groups())
        return {
            "kind": "empty",
            "raw": raw_id,
            "line": line,
            "first": base,
            "second": suffix,
        }

    if raw_id.isdigit():
        raise RowIdError(
            "invalid_token_id",
            raw_id,
            line,
            f"invalid CoNLL-U token id {raw_id} at line {line}",
        )
    raise RowIdError(
        "invalid_id",
        raw_id,
        line,
        f"invalid CoNLL-U row id {raw_id!r} at line {line}",
    )


def validate_sentence_id_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return deterministic sentence-level ID-structure errors.

    Enforced invariants come from the CoNLL-U ID contract relevant to alignment:
    basic words are 1..N in row order; MWT ranges are nonempty, nonoverlapping,
    cover existing basic words and precede their first word; empty-node suffixes
    start at .1 without gaps and occur between their base word (or sentence start
    for base 0) and the following basic word.
    """

    errors: list[dict[str, Any]] = []
    basics = [row for row in rows if row["kind"] == "basic"]
    multiwords = [row for row in rows if row["kind"] == "multiword"]
    empties = [row for row in rows if row["kind"] == "empty"]

    basic_lines: dict[int, int] = {}
    expected = 1
    for row in basics:
        token_id = int(row["first"])
        if token_id in basic_lines:
            errors.append(
                {
                    "kind": "duplicate_token_id",
                    "line": row["line"],
                    "id": row["raw"],
                    "detail": f"duplicate CoNLL-U token id {token_id}",
                }
            )
            continue
        basic_lines[token_id] = int(row["line"])
        if token_id != expected:
            errors.append(
                {
                    "kind": "invalid_id_sequence",
                    "line": row["line"],
                    "id": row["raw"],
                    "detail": f"expected basic word id {expected}, got {token_id}",
                }
            )
            expected = token_id + 1
        else:
            expected += 1

    previous_end = 0
    for row in sorted(multiwords, key=lambda item: (item["first"], item["second"], item["line"])):
        start = int(row["first"])
        end = int(row["second"])
        if start <= previous_end:
            errors.append(
                {
                    "kind": "invalid_id_sequence",
                    "line": row["line"],
                    "id": row["raw"],
                    "detail": "overlapping CoNLL-U multiword ranges",
                }
            )
        previous_end = max(previous_end, end)

        missing = [token_id for token_id in range(start, end + 1) if token_id not in basic_lines]
        if missing:
            errors.append(
                {
                    "kind": "invalid_id_sequence",
                    "line": row["line"],
                    "id": row["raw"],
                    "detail": "multiword range references missing basic word ids",
                }
            )
        elif int(row["line"]) >= basic_lines[start]:
            errors.append(
                {
                    "kind": "invalid_id_sequence",
                    "line": row["line"],
                    "id": row["raw"],
                    "detail": "multiword range must precede its first basic word",
                }
            )

    empties_by_base: dict[int, list[dict[str, Any]]] = {}
    for row in empties:
        empties_by_base.setdefault(int(row["first"]), []).append(row)

    for base in sorted(empties_by_base):
        group = sorted(empties_by_base[base], key=lambda item: item["line"])
        if base != 0 and base not in basic_lines:
            for row in group:
                errors.append(
                    {
                        "kind": "invalid_id_sequence",
                        "line": row["line"],
                        "id": row["raw"],
                        "detail": f"empty-node base word {base} does not exist",
                    }
                )
            continue

        expected_suffix = 1
        for row in group:
            suffix = int(row["second"])
            if suffix != expected_suffix:
                errors.append(
                    {
                        "kind": "invalid_id_sequence",
                        "line": row["line"],
                        "id": row["raw"],
                        "detail": f"expected empty-node suffix .{expected_suffix}, got .{suffix}",
                    }
                )
                expected_suffix = suffix + 1
            else:
                expected_suffix += 1

            row_line = int(row["line"])
            if base == 0:
                if 1 in basic_lines and row_line >= basic_lines[1]:
                    errors.append(
                        {
                            "kind": "invalid_id_sequence",
                            "line": row["line"],
                            "id": row["raw"],
                            "detail": "sentence-initial empty node must precede word 1",
                        }
                    )
            else:
                if row_line <= basic_lines[base]:
                    errors.append(
                        {
                            "kind": "invalid_id_sequence",
                            "line": row["line"],
                            "id": row["raw"],
                            "detail": "empty node must follow its base word",
                        }
                    )
                next_line = basic_lines.get(base + 1)
                if next_line is not None and row_line >= next_line:
                    errors.append(
                        {
                            "kind": "invalid_id_sequence",
                            "line": row["line"],
                            "id": row["raw"],
                            "detail": "empty node must precede the following basic word",
                        }
                    )

            # If the following word starts an MWT, an empty node before that word
            # must also occur before the MWT range line.
            for multiword in multiwords:
                if int(multiword["first"]) == base + 1 and row_line >= int(multiword["line"]):
                    errors.append(
                        {
                            "kind": "invalid_id_sequence",
                            "line": row["line"],
                            "id": row["raw"],
                            "detail": "empty node before an MWT must precede the MWT range",
                        }
                    )
                    break

    return sorted(errors, key=lambda item: (int(item["line"]), item["kind"], item["id"]))
