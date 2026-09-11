"""Validated, non-overwriting CoNLL-U supplementation for parsed TT documents."""

from __future__ import annotations

import html
import re
from typing import Any

from .model import ConlluSupplement, DocumentModel, SupplementalWord


BASIC_ID_RE = re.compile(r"[1-9][0-9]*$")
MWT_ID_RE = re.compile(r"([1-9][0-9]*)-([1-9][0-9]*)$")
EMPTY_ID_RE = re.compile(r"(0|[1-9][0-9]*)\.([1-9][0-9]*)$")


class SupplementUnavailable(ValueError):
    """The supplied CoNLL-U record must not supplement the canonical TT record."""

    def __init__(self, reason: str, source_path: str, detail: str = "") -> None:
        self.reason = reason
        self.source_path = source_path
        self.detail = detail
        message = f"{reason}: {source_path}"
        if detail:
            message += f": {detail}"
        super().__init__(message)


class _MalformedConllu(ValueError):
    pass


def _kv_field(value: str) -> dict[str, str]:
    if value == "_" or value == "":
        return {}
    result: dict[str, str] = {}
    for item in value.split("|"):
        if "=" not in item:
            raise _MalformedConllu(f"attribute {item!r} has no '='")
        key, field_value = item.split("=", 1)
        if not key or key in result:
            raise _MalformedConllu(f"duplicate/empty attribute key {key!r}")
        result[key] = field_value
    return result


def _validate_sentence(rows: list[tuple[int, list[str]]]) -> list[dict[str, Any]]:
    basics: list[dict[str, Any]] = []
    basic_ids: list[int] = []
    basic_lines: dict[int, int] = {}
    mwt_ranges: list[tuple[int, int, int]] = []
    empty_rows: list[tuple[int, int, int]] = []
    empty_ids: set[tuple[int, int]] = set()

    for line_number, columns in rows:
        if len(columns) != 10:
            raise _MalformedConllu(
                f"line {line_number} has {len(columns)} columns instead of 10"
            )
        literal_id = columns[0]
        if BASIC_ID_RE.fullmatch(literal_id):
            token_id = int(literal_id)
            basic_ids.append(token_id)
            if token_id in basic_lines:
                raise _MalformedConllu(f"duplicate basic word ID {token_id}")
            basic_lines[token_id] = line_number
            head_literal = columns[6]
            if not re.fullmatch(r"0|[1-9][0-9]*", head_literal):
                raise _MalformedConllu(f"invalid HEAD {head_literal!r} for word {literal_id}")
            basics.append(
                {
                    "local_id": token_id,
                    "form_literal": columns[1],
                    "form": html.unescape(columns[1]),
                    "lemma": None if columns[2] == "_" else columns[2],
                    "upos": None if columns[3] == "_" else columns[3],
                    "xpos": None if columns[4] == "_" else columns[4],
                    "feats": _kv_field(columns[5]),
                    "head_local": int(head_literal),
                    "deprel": None if columns[7] == "_" else columns[7],
                    "misc": _kv_field(columns[9]),
                }
            )
        elif match := MWT_ID_RE.fullmatch(literal_id):
            start, end = int(match.group(1)), int(match.group(2))
            if start >= end:
                raise _MalformedConllu(f"reversed/empty multiword range {literal_id!r}")
            mwt_ranges.append((start, end, line_number))
        elif match := EMPTY_ID_RE.fullmatch(literal_id):
            empty_id = (int(match.group(1)), int(match.group(2)))
            if empty_id in empty_ids:
                raise _MalformedConllu(f"duplicate empty-node ID {literal_id!r}")
            empty_ids.add(empty_id)
            empty_rows.append((empty_id[0], empty_id[1], line_number))
        else:
            raise _MalformedConllu(f"invalid CoNLL-U ID {literal_id!r}")

    expected = list(range(1, len(basic_ids) + 1))
    if basic_ids != expected:
        raise _MalformedConllu(
            f"basic word IDs must be consecutive from 1; observed {basic_ids[:20]!r}"
        )
    basic_set = set(basic_ids)

    previous_end = 0
    for start, end, line_number in sorted(mwt_ranges):
        if start <= previous_end:
            raise _MalformedConllu(f"overlapping multiword range {start}-{end}")
        previous_end = end
        if any(token_id not in basic_set for token_id in range(start, end + 1)):
            raise _MalformedConllu(f"multiword range {start}-{end} references missing basic word")
        if line_number >= basic_lines[start]:
            raise _MalformedConllu(
                f"multiword range {start}-{end} must precede its first basic word"
            )

    empties_by_base: dict[int, list[tuple[int, int]]] = {}
    for base, suffix, line_number in empty_rows:
        empties_by_base.setdefault(base, []).append((suffix, line_number))
    for base, group in sorted(empties_by_base.items()):
        if base != 0 and base not in basic_lines:
            raise _MalformedConllu(f"empty-node base word {base} does not exist")
        ordered = sorted(group, key=lambda item: item[1])
        expected_suffix = 1
        for suffix, line_number in ordered:
            if suffix != expected_suffix:
                raise _MalformedConllu(
                    f"expected empty-node suffix .{expected_suffix} after base {base}, got .{suffix}"
                )
            expected_suffix += 1
            if base == 0:
                if 1 in basic_lines and line_number >= basic_lines[1]:
                    raise _MalformedConllu("sentence-initial empty node must precede word 1")
            else:
                if line_number <= basic_lines[base]:
                    raise _MalformedConllu("empty node must follow its base word")
                following = basic_lines.get(base + 1)
                if following is not None and line_number >= following:
                    raise _MalformedConllu("empty node must precede the following basic word")
                for mwt_start, _mwt_end, mwt_line in mwt_ranges:
                    if mwt_start == base + 1 and line_number >= mwt_line:
                        raise _MalformedConllu("empty node before an MWT must precede its MWT row")

    for token in basics:
        head = token["head_local"]
        if head and head not in basic_set:
            raise _MalformedConllu(
                f"HEAD {head} for word {token['local_id']} is not a sentence word"
            )
    return basics


def _parse_sentences(text: str) -> list[list[dict[str, Any]]]:
    sentence_rows: list[tuple[int, list[str]]] = []
    sentences: list[list[dict[str, Any]]] = []

    def flush() -> None:
        nonlocal sentence_rows
        if sentence_rows:
            sentences.append(_validate_sentence(sentence_rows))
            sentence_rows = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            flush()
            continue
        if line.startswith("#"):
            continue
        sentence_rows.append((line_number, line.split("\t")))
    flush()
    return sentences


def parse_conllu_supplement(
    document: DocumentModel,
    raw: bytes,
    *,
    source_path: str,
) -> ConlluSupplement:
    """Validate and align one CoNLL-U record without mutating TT source values."""

    text = raw.decode("utf-8")
    if not text.strip():
        raise SupplementUnavailable("placeholder", source_path)
    try:
        sentences = _parse_sentences(text)
    except _MalformedConllu as exc:
        raise SupplementUnavailable("malformed_conllu", source_path, str(exc)) from exc

    basic_count = sum(len(sentence) for sentence in sentences)
    if basic_count != len(document.words):
        raise SupplementUnavailable(
            "token_alignment",
            source_path,
            f"CoNLL-U has {basic_count} basic words but TT has {len(document.words)}",
        )
    if len(sentences) != len(document.sentences) or [
        len(sentence) for sentence in sentences
    ] != [len(sentence.word_ordinals) for sentence in document.sentences]:
        raise SupplementUnavailable(
            "token_alignment",
            source_path,
            "sentence boundaries/cardinalities differ from TT",
        )

    result: list[SupplementalWord] = []
    absolute_offset = 0
    for sentence in sentences:
        for token in sentence:
            absolute_ordinal = absolute_offset + token["local_id"]
            canonical = document.words[absolute_ordinal - 1]
            if canonical.norm != token["form"]:
                raise SupplementUnavailable(
                    "token_alignment",
                    source_path,
                    f"word {absolute_ordinal} norm differs: TT={canonical.norm!r}, CoNLL-U={token['form']!r}",
                )
            local_head = token["head_local"]
            head_ordinal = 0 if local_head == 0 else absolute_offset + local_head
            result.append(
                SupplementalWord(
                    ordinal=absolute_ordinal,
                    form_literal=token["form_literal"],
                    form=token["form"],
                    lemma=token["lemma"],
                    upos=token["upos"],
                    xpos=token["xpos"],
                    feats=dict(token["feats"]),
                    head_ordinal=head_ordinal,
                    deprel=token["deprel"],
                    misc=dict(token["misc"]),
                )
            )
        absolute_offset += len(sentence)

    return ConlluSupplement(source_path=source_path, words=tuple(result))
