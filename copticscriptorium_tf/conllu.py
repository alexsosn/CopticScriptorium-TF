"""Validated, non-overwriting CoNLL-U supplementation for parsed TT documents."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import html
from pathlib import Path
import re
from sys import intern
from types import MappingProxyType
from typing import Any, Iterable, Mapping
import zipfile

from .model import ConlluSupplement, DocumentModel, SupplementalWord


BASIC_ID_RE = re.compile(r"[1-9][0-9]*$")
MWT_ID_RE = re.compile(r"([1-9][0-9]*)-([1-9][0-9]*)$")
EMPTY_ID_RE = re.compile(r"(0|[1-9][0-9]*)\.([1-9][0-9]*)$")

# About two million supplemental words are retained during full-corpus
# conversion. Share the empty attribute mapping and intern repeated strings.
_EMPTY: Mapping[str, str] = MappingProxyType({})


def _value(column: str) -> str | None:
    return None if column == "_" else intern(column)


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


class _UnsupportedConlluShape(ValueError):
    pass


def _kv_field(value: str) -> Mapping[str, str]:
    if value == "_" or value == "":
        return _EMPTY
    result: dict[str, str] = {}
    for item in value.split("|"):
        if "=" not in item:
            raise _MalformedConllu(f"attribute {item!r} has no '='")
        key, field_value = item.split("=", 1)
        if not key or key in result:
            raise _MalformedConllu(f"duplicate/empty attribute key {key!r}")
        result[intern(key)] = intern(field_value)
    return result


def _validate_sentence(rows: list[tuple[int, list[str]]]) -> list[dict[str, Any]]:
    basics: list[dict[str, Any]] = []
    basic_ids: list[int] = []
    basic_lines: dict[int, int] = {}
    mwt_ranges: list[tuple[int, int, int]] = []
    empty_rows: list[tuple[int, int, int]] = []
    empty_ids: set[tuple[int, int]] = set()
    has_enhanced_deps = False

    for line_number, columns in rows:
        if len(columns) != 10:
            raise _MalformedConllu(
                f"line {line_number} has {len(columns)} columns instead of 10"
            )
        if columns[8] not in {"", "_"}:
            has_enhanced_deps = True
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
                    "form_literal": intern(columns[1]),
                    "form": intern(html.unescape(columns[1])),
                    "lemma": _value(columns[2]),
                    "upos": _value(columns[3]),
                    "xpos": _value(columns[4]),
                    "feats": _kv_field(columns[5]),
                    "head_local": int(head_literal),
                    "deprel": _value(columns[7]),
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

    if empty_rows:
        raise _UnsupportedConlluShape(
            "empty-node rows are not part of the reviewed supplementation model"
        )
    if has_enhanced_deps:
        raise _UnsupportedConlluShape(
            "enhanced DEPS are not part of the reviewed supplementation model"
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

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SupplementUnavailable("invalid_utf8", source_path, str(exc)) from exc
    if not text.strip():
        raise SupplementUnavailable("placeholder", source_path)
    try:
        sentences = _parse_sentences(text)
    except _UnsupportedConlluShape as exc:
        raise SupplementUnavailable(
            "unsupported_conllu_shape", source_path, str(exc)
        ) from exc
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
                    feats=token["feats"],
                    head_ordinal=head_ordinal,
                    deprel=token["deprel"],
                    misc=token["misc"],
                )
            )
        absolute_offset += len(sentence)

    return ConlluSupplement(source_path=source_path, words=tuple(result))


SUPPLEMENTED = "supplemented"
MISSING = "missing"


@dataclass(frozen=True, slots=True)
class ConlluLocator:
    """Where one CoNLL-U source record lives; its bytes are read on demand."""

    source_record_id: str
    source_path: str
    filesystem_path: Path
    member: str | None = None


@dataclass(frozen=True, slots=True)
class ConlluReport:
    """Operational outcome of pairing TT documents with CoNLL-U records."""

    supplemented_source_records: int
    unavailable_source_records: tuple[dict[str, str], ...]
    missing_source_records: tuple[str, ...]
    records_without_tt: tuple[str, ...]


def _source_record_id(corpus: str, dataset: str, record: str) -> str:
    return f"{corpus}/{dataset}:{record}"


def discover_conllu_records(root: Path | str) -> dict[str, ConlluLocator]:
    """Locate supported CoNLL-U records, keyed by case-folded source_record_id.

    Packaging rules mirror TT discovery: ``corpus/dataset_CONLLU/*.conllu`` and
    ``corpus/dataset_CONLLU.zip`` members that are root-level or directly under
    ``dataset_CONLLU/``. Unsupported layouts fail closed rather than being guessed.
    """

    root_path = Path(root)
    found: list[ConlluLocator] = []

    for directory in sorted(root_path.rglob("*_CONLLU"), key=lambda path: path.as_posix()):
        relative = directory.relative_to(root_path)
        if directory.is_symlink():
            raise ValueError(
                f"symlinked CoNLL-U dataset directory is unsupported: {relative.as_posix()!r}"
            )
        if not directory.is_dir():
            raise ValueError(
                f"CoNLL-U dataset candidate must be a directory: {relative.as_posix()!r}"
            )
        if len(relative.parts) != 2:
            raise ValueError(f"unsupported CoNLL-U dataset layout: {relative.as_posix()!r}")
        corpus = relative.parts[0]
        dataset = relative.parts[1][: -len("_CONLLU")]
        candidates = sorted(
            (item for item in directory.rglob("*") if item.suffix.casefold() == ".conllu"),
            key=lambda item: item.as_posix(),
        )
        records_before = len(found)
        for path in candidates:
            source_path = path.relative_to(root_path).as_posix()
            if path.is_symlink():
                raise ValueError(f"symlinked CoNLL-U source record is unsupported: {source_path!r}")
            if not path.is_file():
                raise ValueError(
                    f"CoNLL-U source record candidate must be a regular file: {source_path!r}"
                )
            logical = path.relative_to(directory)
            if len(logical.parts) != 1:
                raise ValueError(
                    f"unsupported CoNLL-U directory member layout in {relative.as_posix()}: "
                    f"{logical.as_posix()!r}"
                )
            record = logical.name[: -len(path.suffix)]
            found.append(
                ConlluLocator(_source_record_id(corpus, dataset, record), source_path, path)
            )
        if len(found) == records_before:
            raise ValueError(
                f"CoNLL-U dataset contains no supported CoNLL-U records: {relative.as_posix()!r}"
            )

    for archive_path in sorted(root_path.rglob("*_CONLLU.zip"), key=lambda path: path.as_posix()):
        relative = archive_path.relative_to(root_path)
        if archive_path.is_symlink():
            raise ValueError(
                f"symlinked CoNLL-U archive package is unsupported: {relative.as_posix()!r}"
            )
        if not archive_path.is_file():
            raise ValueError(
                f"CoNLL-U archive package must be a regular file: {relative.as_posix()!r}"
            )
        if len(relative.parts) != 2:
            raise ValueError(f"unsupported CoNLL-U dataset layout: {relative.as_posix()!r}")
        corpus = relative.parts[0]
        dataset = relative.parts[1][: -len("_CONLLU.zip")]
        expected_prefix = f"{dataset}_CONLLU/"
        records_before = len(found)
        with zipfile.ZipFile(archive_path) as archive:
            for member in sorted(archive.namelist()):
                if member.endswith("/") or not member.casefold().endswith(".conllu"):
                    continue
                if "/" not in member:
                    logical = member
                elif member.startswith(expected_prefix):
                    logical = member[len(expected_prefix):]
                    if not logical or "/" in logical:
                        raise ValueError(
                            f"unsupported CoNLL-U archive member layout in "
                            f"{relative.as_posix()}: {member!r}"
                        )
                else:
                    raise ValueError(
                        f"unsupported CoNLL-U archive member layout in "
                        f"{relative.as_posix()}: {member!r}"
                    )
                record = logical[: -len(".conllu")]
                found.append(
                    ConlluLocator(
                        _source_record_id(corpus, dataset, record),
                        f"{relative.as_posix()}!/{member}",
                        archive_path,
                        member,
                    )
                )
        if len(found) == records_before:
            raise ValueError(
                f"CoNLL-U archive contains no supported CoNLL-U records: {relative.as_posix()!r}"
            )

    result: dict[str, ConlluLocator] = {}
    for locator in found:
        key = locator.source_record_id.casefold()
        previous = result.get(key)
        if previous is not None:
            raise ValueError(
                f"CoNLL-U source-record collision: {previous.source_path!r} "
                f"versus {locator.source_path!r}"
            )
        result[key] = locator
    return result


def attach_conllu_supplements(
    documents: Iterable[DocumentModel],
    root: Path | str,
) -> tuple[list[DocumentModel], ConlluReport]:
    """Pair TT documents with CoNLL-U counterparts and record every outcome.

    TT remains canonical: a document is never altered except for the separate
    ``conllu_*`` fields, and CoNLL-U records without a TT counterpart are reported
    rather than converted.
    """

    locators = discover_conllu_records(root)
    archives: dict[Path, zipfile.ZipFile] = {}
    attached: list[DocumentModel] = []
    unavailable: list[dict[str, str]] = []
    missing: list[str] = []
    supplemented = 0
    try:
        for document in documents:
            locator = locators.pop(document.source_record_id.casefold(), None)
            if locator is None:
                missing.append(document.source_record_id)
                attached.append(replace(document, conllu_status=MISSING))
                continue
            if locator.member is None:
                raw = locator.filesystem_path.read_bytes()
            else:
                archive = archives.get(locator.filesystem_path)
                if archive is None:
                    archive = zipfile.ZipFile(locator.filesystem_path)
                    archives[locator.filesystem_path] = archive
                raw = archive.read(locator.member)
            provenance = {
                "conllu_source_path": locator.source_path,
                "conllu_source_sha256": sha256(raw).hexdigest(),
            }
            try:
                supplement = parse_conllu_supplement(
                    document, raw, source_path=locator.source_path
                )
            except SupplementUnavailable as exc:
                unavailable.append({
                    "source_record_id": document.source_record_id,
                    "conllu_source_path": locator.source_path,
                    "reason": exc.reason,
                    "detail": exc.detail,
                })
                attached.append(replace(document, conllu_status=exc.reason, **provenance))
                continue
            supplemented += 1
            attached.append(replace(
                document,
                conllu_status=SUPPLEMENTED,
                conllu_words=supplement.words,
                **provenance,
            ))
    finally:
        for archive in archives.values():
            archive.close()

    report = ConlluReport(
        supplemented_source_records=supplemented,
        unavailable_source_records=tuple(sorted(
            unavailable,
            key=lambda item: (item["source_record_id"].casefold(), item["source_record_id"]),
        )),
        missing_source_records=tuple(missing),
        records_without_tt=tuple(sorted(
            (locator.source_path for locator in locators.values()),
            key=lambda path: (path.casefold(), path),
        )),
    )
    return attached, report
