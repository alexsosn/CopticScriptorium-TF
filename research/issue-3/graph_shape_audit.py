"""Corpus-wide TT graph-shape census for CopticScriptorium-TF issue #3.

The source TT stream is overlapping SGML, not XML. This audit therefore scans
start/end tags as events and keeps independent semantic stacks for linguistic
structures while allowing layout spans to cross an open ``norm`` token.
"""

from __future__ import annotations

import argparse
from collections import Counter
import html
import json
from pathlib import Path
import re
from typing import Any, Iterator
import zipfile


TAG_RE = re.compile(r"<(/?)([A-Za-z_][A-Za-z0-9_.:-]*)([^>]*)>")
ATTR_RE = re.compile(r'\s+([A-Za-z_][A-Za-z0-9_.:-]*)\s*=\s*"([^"]*)"')
LAYOUT_TAGS = {
    "pb_xml_id": ("page", "pb_xml_id"),
    "cb_n": ("column", "cb_n"),
    "lb_n": ("line", "lb_n"),
}
GROUP_HISTOGRAM_KEYS = (
    "orig_group_to_norm_group",
    "norm_group_to_orig",
    "orig_to_norm",
)


def _attrs(fragment: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, value in ATTR_RE.findall(fragment):
        if name in attrs:
            raise ValueError(f"duplicate TT tag attribute {name!r}")
        attrs[name] = html.unescape(value)
    return attrs


def _visible_token_piece(value: str) -> str:
    return "".join(
        character for character in html.unescape(value) if not character.isspace()
    )


def _source_record_id(corpus: str, dataset: str, record: str) -> str:
    return f"{corpus}/{dataset}:{record}"


def _iter_direct(root: Path) -> Iterator[dict[str, Any]]:
    for directory in sorted(
        (path for path in root.rglob("*_TT") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        relative = directory.relative_to(root)
        if len(relative.parts) != 2 or not relative.parts[1].endswith("_TT"):
            continue
        corpus = relative.parts[0]
        dataset = relative.parts[1][:-3]
        for path in sorted(
            (
                item
                for item in directory.rglob("*")
                if item.is_file() and item.suffix.casefold() == ".tt"
            ),
            key=lambda item: item.as_posix(),
        ):
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            relative_record = path.relative_to(directory).as_posix()
            record = relative_record[: -len(path.suffix)]
            yield {
                "corpus": corpus,
                "dataset": dataset,
                "record": record,
                "source_record_id": _source_record_id(corpus, dataset, record),
                "source": path.relative_to(root).as_posix(),
                "packaging": "directory",
                "text": text,
            }


def _iter_archives(root: Path) -> Iterator[dict[str, Any]]:
    for archive_path in sorted(root.rglob("*_TT.zip"), key=lambda path: path.as_posix()):
        relative = archive_path.relative_to(root)
        if len(relative.parts) != 2 or not relative.parts[1].endswith("_TT.zip"):
            continue
        corpus = relative.parts[0]
        dataset = relative.parts[1][:-7]
        expected_prefix = f"{dataset}_TT/"
        with zipfile.ZipFile(archive_path) as archive:
            for member in sorted(archive.namelist()):
                if member.endswith("/") or not member.casefold().endswith(".tt"):
                    continue
                if "/" not in member:
                    logical = member
                elif member.startswith(expected_prefix):
                    logical = member[len(expected_prefix) :]
                    if not logical:
                        raise ValueError(
                            f"empty TT archive member path in {relative.as_posix()}: {member!r}"
                        )
                else:
                    raise ValueError(
                        f"unsupported TT archive member layout in {relative.as_posix()}: {member!r}"
                    )
                raw = archive.read(member)
                text = raw.decode("utf-8")
                record = logical[:-3]
                yield {
                    "corpus": corpus,
                    "dataset": dataset,
                    "record": record,
                    "source_record_id": _source_record_id(corpus, dataset, record),
                    "source": f"{relative.as_posix()}!/{member}",
                    "packaging": "archive",
                    "text": text,
                }


def iter_tt_records(root: Path | str) -> Iterator[dict[str, Any]]:
    root_path = Path(root)
    yield from _iter_direct(root_path)
    yield from _iter_archives(root_path)


def _counter_json(counter: Counter[int]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def _string_counter_json(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _analyze_document(record: dict[str, Any]) -> dict[str, Any]:
    text = record["text"]
    source_record_id = record["source_record_id"]

    orig_group_stack: list[dict[str, int]] = []
    norm_group_stack: list[dict[str, int]] = []
    orig_stack: list[dict[str, int]] = []
    entity_stack: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    translation_stack: list[dict[str, Any]] = []
    translations: list[dict[str, Any]] = []
    arabic_translation_stack: list[dict[str, Any]] = []
    arabic_translations: list[dict[str, Any]] = []
    token_ids: set[str] = set()
    current_norm: dict[str, Any] | None = None

    counts = Counter()
    sentence_starts = 0
    first_token_new_sent: bool | None = None
    first_sentence_token_position: int | None = None
    token_position = 0

    group_histograms: dict[str, Counter[int]] = {
        key: Counter() for key in GROUP_HISTOGRAM_KEYS
    }
    norm_group_parent_contexts: Counter[str] = Counter()
    norm_parent_contexts: Counter[str] = Counter()
    layout_counts: Counter[str] = Counter()
    active_layout: dict[str, str | None] = {
        "page": None,
        "column": None,
        "line": None,
    }
    last_layout: dict[str, str | None] = {
        "page": None,
        "column": None,
        "line": None,
    }
    crossings: list[dict[str, Any]] = []

    translation_count = 0
    arabic_translation_count = 0
    empty_translation_count = 0
    empty_arabic_translation_count = 0
    chapter_marker_count = 0
    verse_marker_count = 0
    video_marker_count = 0
    nested_entity_count = 0

    def append_norm_text(fragment: str) -> None:
        if current_norm is None:
            return
        piece = _visible_token_piece(fragment)
        if piece:
            current_norm["text_parts"].append(piece)

    def current_norm_offset() -> int:
        if current_norm is None:
            return 0
        return sum(len(piece) for piece in current_norm["text_parts"])

    cursor = 0
    for match in TAG_RE.finditer(text):
        append_norm_text(text[cursor : match.start()])
        cursor = match.end()

        is_close = bool(match.group(1))
        name = match.group(2)
        if is_close or name == "meta":
            attrs = {}
        else:
            attrs = _attrs(match.group(3))

        if is_close:
            if name == "norm":
                if current_norm is None:
                    raise ValueError(f"closing norm without open norm in {source_record_id}")
                token_text = "".join(current_norm["text_parts"])
                for candidate in current_norm["layout_candidates"]:
                    offset = candidate["char_offset"]
                    if 0 < offset < len(token_text):
                        crossings.append({**candidate, "token_text": token_text})
                current_norm = None
            elif name == "orig":
                if not orig_stack:
                    raise ValueError(f"closing orig without open orig in {source_record_id}")
                group_histograms["orig_to_norm"][orig_stack.pop()["norm_count"]] += 1
            elif name == "norm_group":
                if not norm_group_stack:
                    raise ValueError(
                        f"closing norm_group without open norm_group in {source_record_id}"
                    )
                group_histograms["norm_group_to_orig"][
                    norm_group_stack.pop()["orig_count"]
                ] += 1
            elif name == "orig_group":
                if not orig_group_stack:
                    raise ValueError(
                        f"closing orig_group without open orig_group in {source_record_id}"
                    )
                group_histograms["orig_group_to_norm_group"][
                    orig_group_stack.pop()["norm_group_count"]
                ] += 1
            elif name == "entity":
                if not entity_stack:
                    raise ValueError(f"closing entity without open entity in {source_record_id}")
                entities.append(entity_stack.pop())
            elif name == "translation":
                if not translation_stack:
                    raise ValueError(
                        f"closing translation without open translation in {source_record_id}"
                    )
                translations.append(translation_stack.pop())
            elif name in {"arabic", "arabic_translation"}:
                if not arabic_translation_stack:
                    raise ValueError(
                        f"closing {name} without open Arabic translation in {source_record_id}"
                    )
                arabic_translations.append(arabic_translation_stack.pop())
            elif name in LAYOUT_TAGS:
                kind, _ = LAYOUT_TAGS[name]
                active_layout[kind] = None
            continue

        if name == "orig_group":
            counts["orig_group"] += 1
            orig_group_stack.append({"norm_group_count": 0})
        elif name == "norm_group":
            counts["norm_group"] += 1
            if orig_group_stack:
                orig_group_stack[-1]["norm_group_count"] += 1
                norm_group_parent_contexts["orig_group"] += 1
            else:
                norm_group_parent_contexts["none"] += 1
            norm_group_stack.append({"orig_count": 0})
        elif name == "orig":
            counts["orig"] += 1
            if not norm_group_stack:
                raise ValueError(f"orig outside norm_group in {source_record_id}")
            norm_group_stack[-1]["orig_count"] += 1
            orig_stack.append({"norm_count": 0})
        elif name == "norm":
            if current_norm is not None:
                raise ValueError(f"nested norm tags in {source_record_id}")
            counts["norm"] += 1
            token_position += 1
            if orig_stack:
                orig_stack[-1]["norm_count"] += 1
                norm_parent_contexts["orig"] += 1
            elif norm_group_stack:
                norm_parent_contexts["norm_group"] += 1
            else:
                raise ValueError(f"norm outside norm_group in {source_record_id}")
            token_id = attrs.get("xml:id")
            if token_id:
                if token_id in token_ids:
                    raise ValueError(
                        f"duplicate norm xml:id {token_id!r} in {source_record_id}"
                    )
                token_ids.add(token_id)
            new_sent = (attrs.get("new_sent") or "").casefold() == "true"
            if first_token_new_sent is None:
                first_token_new_sent = new_sent
            if new_sent:
                sentence_starts += 1
                if first_sentence_token_position is None:
                    first_sentence_token_position = token_position
            current_norm = {
                "token_id": token_id,
                "text_parts": [],
                "layout_candidates": [],
            }
            for entity in entity_stack:
                entity["token_ids"].append(token_id)
            for translation in translation_stack:
                translation["token_count"] += 1
            for translation in arabic_translation_stack:
                translation["token_count"] += 1
        elif name in LAYOUT_TAGS:
            kind, value_attribute = LAYOUT_TAGS[name]
            value = attrs.get(value_attribute)
            layout_counts[kind] += 1
            if current_norm is not None and last_layout[kind] is not None:
                current_norm["layout_candidates"].append(
                    {
                        "source_record_id": source_record_id,
                        "source": record["source"],
                        "token_id": current_norm["token_id"],
                        "kind": kind,
                        "from_value": last_layout[kind],
                        "to_value": value,
                        "char_offset": current_norm_offset(),
                    }
                )
            active_layout[kind] = value
            last_layout[kind] = value
        elif name == "entity":
            if entity_stack:
                nested_entity_count += 1
            entity_stack.append(
                {
                    "attrs": attrs,
                    "token_ids": [current_norm["token_id"]]
                    if current_norm is not None
                    else [],
                }
            )
        elif name == "translation":
            translation_count += 1
            literal = attrs.get("translation") or ""
            if not literal:
                empty_translation_count += 1
            translation_stack.append(
                {
                    "text": literal,
                    "token_count": 1 if current_norm is not None else 0,
                    "source_record_id": source_record_id,
                    "source": record["source"],
                    "after_token_position": token_position,
                    "source_char_offset": match.start(),
                }
            )
        elif name in {"arabic", "arabic_translation"}:
            arabic_translation_count += 1
            value = attrs.get("arabic") or attrs.get("arabic_translation") or ""
            if not value:
                empty_arabic_translation_count += 1
            arabic_translation_stack.append(
                {
                    "text": value,
                    "token_count": 1 if current_norm is not None else 0,
                    "source_record_id": source_record_id,
                    "source": record["source"],
                    "after_token_position": token_position,
                    "source_char_offset": match.start(),
                }
            )
        elif name == "chapter_n":
            chapter_marker_count += 1
        elif name == "verse_n":
            verse_marker_count += 1
        elif name == "vid_n":
            video_marker_count += 1

    append_norm_text(text[cursor:])

    if current_norm is not None:
        raise ValueError(f"unclosed norm in {source_record_id}")
    if orig_stack or norm_group_stack or orig_group_stack:
        raise ValueError(f"unclosed linguistic grouping tag in {source_record_id}")
    if entity_stack:
        raise ValueError(f"unclosed entity tag in {source_record_id}")
    if translation_stack:
        raise ValueError(f"unclosed translation tag in {source_record_id}")
    if arabic_translation_stack:
        raise ValueError(f"unclosed Arabic translation tag in {source_record_id}")

    entity_missing_head = 0
    entity_unresolved_head = 0
    entity_head_outside_span = 0
    entity_heads_outside_span: list[dict[str, Any]] = []
    entity_empty = 0
    entity_identity_count = 0
    entity_without_identity_count = 0
    entity_token_counts: Counter[int] = Counter()
    entity_class_counts: Counter[str] = Counter()
    for entity in entities:
        ids = [token_id for token_id in entity["token_ids"] if token_id is not None]
        entity_token_counts[len(ids)] += 1
        if not ids:
            entity_empty += 1
        entity_class = entity["attrs"].get("entity")
        if entity_class:
            entity_class_counts[entity_class] += 1
        identity = entity["attrs"].get("identity")
        if identity:
            entity_identity_count += 1
        else:
            entity_without_identity_count += 1
        head = entity["attrs"].get("head_tok")
        if not head:
            entity_missing_head += 1
        else:
            target = head[1:] if head.startswith("#") else head
            if target not in token_ids:
                entity_unresolved_head += 1
            elif target not in ids:
                entity_head_outside_span += 1
                entity_heads_outside_span.append(
                    {
                        "source_record_id": source_record_id,
                        "source": record["source"],
                        "entity_class": entity_class,
                        "identity": identity,
                        "head_tok": head,
                        "target_token_id": target,
                        "span_token_ids": ids,
                    }
                )

    translation_token_counts: Counter[int] = Counter()
    translation_empty_text_by_span: Counter[str] = Counter()
    translation_zero_span_examples: list[dict[str, Any]] = []
    for translation in translations:
        count = int(translation["token_count"])
        translation_token_counts[count] += 1
        if not translation["text"]:
            translation_empty_text_by_span["zero" if count == 0 else "nonzero"] += 1
        if count == 0:
            translation_zero_span_examples.append(translation)

    arabic_translation_token_counts: Counter[int] = Counter()
    arabic_translation_empty_text_by_span: Counter[str] = Counter()
    arabic_translation_zero_span_examples: list[dict[str, Any]] = []
    for translation in arabic_translations:
        count = int(translation["token_count"])
        arabic_translation_token_counts[count] += 1
        if not translation["text"]:
            arabic_translation_empty_text_by_span["zero" if count == 0 else "nonzero"] += 1
        if count == 0:
            arabic_translation_zero_span_examples.append(translation)

    return {
        "source_record_id": source_record_id,
        "source": record["source"],
        "packaging": record["packaging"],
        "orig_group_count": counts["orig_group"],
        "norm_group_count": counts["norm_group"],
        "orig_count": counts["orig"],
        "norm_count": counts["norm"],
        "sentence_start_count": sentence_starts,
        "first_token_new_sent": first_token_new_sent,
        "first_sentence_token_position": first_sentence_token_position,
        "group_histograms": {
            key: _counter_json(group_histograms[key]) for key in GROUP_HISTOGRAM_KEYS
        },
        "norm_group_parent_contexts": _string_counter_json(norm_group_parent_contexts),
        "norm_parent_contexts": _string_counter_json(norm_parent_contexts),
        "layout_counts": _string_counter_json(layout_counts),
        "layout_crossings": crossings,
        "entity_count": len(entities),
        "entity_missing_head_count": entity_missing_head,
        "entity_unresolved_head_count": entity_unresolved_head,
        "entity_head_outside_span_count": entity_head_outside_span,
        "entity_heads_outside_span": entity_heads_outside_span,
        "entity_empty_count": entity_empty,
        "entity_identity_count": entity_identity_count,
        "entity_without_identity_count": entity_without_identity_count,
        "entity_token_count_histogram": _counter_json(entity_token_counts),
        "entity_class_counts": _string_counter_json(entity_class_counts),
        "nested_entity_count": nested_entity_count,
        "translation_count": translation_count,
        "translation_token_count_histogram": _counter_json(translation_token_counts),
        "translation_empty_text_by_span": _string_counter_json(
            translation_empty_text_by_span
        ),
        "translation_zero_span_examples": translation_zero_span_examples,
        "arabic_translation_count": arabic_translation_count,
        "arabic_translation_token_count_histogram": _counter_json(
            arabic_translation_token_counts
        ),
        "arabic_translation_empty_text_by_span": _string_counter_json(
            arabic_translation_empty_text_by_span
        ),
        "arabic_translation_zero_span_examples": arabic_translation_zero_span_examples,
        "empty_translation_count": empty_translation_count,
        "empty_arabic_translation_count": empty_arabic_translation_count,
        "chapter_marker_count": chapter_marker_count,
        "verse_marker_count": verse_marker_count,
        "video_marker_count": video_marker_count,
    }


def audit_upstream(root: Path | str) -> dict[str, Any]:
    records = sorted(iter_tt_records(root), key=lambda item: item["source_record_id"])
    documents = [_analyze_document(record) for record in records]

    totals = Counter()
    group_histograms: dict[str, Counter[int]] = {
        key: Counter() for key in GROUP_HISTOGRAM_KEYS
    }
    norm_group_parent_contexts: Counter[str] = Counter()
    norm_parent_contexts: Counter[str] = Counter()
    layout_counts: Counter[str] = Counter()
    layout_crossings: list[dict[str, Any]] = []
    entity_token_counts: Counter[int] = Counter()
    entity_class_counts: Counter[str] = Counter()
    translation_token_counts: Counter[int] = Counter()
    translation_empty_text_by_span: Counter[str] = Counter()
    translation_zero_span_examples: list[dict[str, Any]] = []
    arabic_translation_token_counts: Counter[int] = Counter()
    arabic_translation_empty_text_by_span: Counter[str] = Counter()
    arabic_translation_zero_span_examples: list[dict[str, Any]] = []
    first_token_not_sentence_start: list[str] = []
    first_sentence_after_first_token: list[dict[str, Any]] = []
    documents_with_marker: Counter[str] = Counter()
    entity_heads_outside_span: list[dict[str, Any]] = []

    for document in documents:
        for key in (
            "orig_group_count",
            "norm_group_count",
            "orig_count",
            "norm_count",
            "sentence_start_count",
            "entity_count",
            "entity_missing_head_count",
            "entity_unresolved_head_count",
            "entity_head_outside_span_count",
            "entity_empty_count",
            "entity_identity_count",
            "entity_without_identity_count",
            "nested_entity_count",
            "translation_count",
            "empty_translation_count",
            "arabic_translation_count",
            "empty_arabic_translation_count",
            "chapter_marker_count",
            "verse_marker_count",
            "video_marker_count",
        ):
            totals[key] += int(document[key])
        for histogram_name in GROUP_HISTOGRAM_KEYS:
            for raw_key, value in document["group_histograms"][histogram_name].items():
                group_histograms[histogram_name][int(raw_key)] += int(value)
        norm_group_parent_contexts.update(document["norm_group_parent_contexts"])
        norm_parent_contexts.update(document["norm_parent_contexts"])
        layout_counts.update(document["layout_counts"])
        layout_crossings.extend(document["layout_crossings"])
        entity_token_counts.update(
            {int(key): value for key, value in document["entity_token_count_histogram"].items()}
        )
        entity_class_counts.update(document["entity_class_counts"])
        translation_token_counts.update(
            {int(key): value for key, value in document["translation_token_count_histogram"].items()}
        )
        translation_empty_text_by_span.update(document["translation_empty_text_by_span"])
        translation_zero_span_examples.extend(document["translation_zero_span_examples"])
        arabic_translation_token_counts.update(
            {
                int(key): value
                for key, value in document["arabic_translation_token_count_histogram"].items()
            }
        )
        arabic_translation_empty_text_by_span.update(
            document["arabic_translation_empty_text_by_span"]
        )
        arabic_translation_zero_span_examples.extend(
            document["arabic_translation_zero_span_examples"]
        )
        if document["first_token_new_sent"] is False:
            first_token_not_sentence_start.append(document["source_record_id"])
        if (
            document["first_sentence_token_position"] is not None
            and document["first_sentence_token_position"] != 1
        ):
            first_sentence_after_first_token.append(
                {
                    "source_record_id": document["source_record_id"],
                    "token_position": document["first_sentence_token_position"],
                }
            )
        for key, output_name in (
            ("chapter_marker_count", "chapter"),
            ("verse_marker_count", "verse"),
            ("video_marker_count", "video"),
        ):
            if document[key]:
                documents_with_marker[output_name] += 1
        entity_heads_outside_span.extend(document["entity_heads_outside_span"])

    return {
        "document_count": len(documents),
        "packaging_counts": _string_counter_json(Counter(d["packaging"] for d in documents)),
        "totals": {key: totals[key] for key in sorted(totals)},
        "group_histograms": {
            key: _counter_json(group_histograms[key]) for key in GROUP_HISTOGRAM_KEYS
        },
        "norm_group_parent_contexts": _string_counter_json(norm_group_parent_contexts),
        "norm_parent_contexts": _string_counter_json(norm_parent_contexts),
        "layout_counts": _string_counter_json(layout_counts),
        "layout_crossing_count": len(layout_crossings),
        "layout_crossing_kind_counts": _string_counter_json(
            Counter(item["kind"] for item in layout_crossings)
        ),
        "layout_crossing_examples": layout_crossings[:100],
        "entity_token_count_histogram": _counter_json(entity_token_counts),
        "entity_class_counts": _string_counter_json(entity_class_counts),
        "entity_head_outside_span_count": len(entity_heads_outside_span),
        "entity_heads_outside_span": entity_heads_outside_span,
        "translation_token_count_histogram": _counter_json(translation_token_counts),
        "translation_empty_text_by_span": _string_counter_json(
            translation_empty_text_by_span
        ),
        "translation_zero_span_count": translation_token_counts[0],
        "translation_zero_span_examples": translation_zero_span_examples[:100],
        "arabic_translation_token_count_histogram": _counter_json(
            arabic_translation_token_counts
        ),
        "arabic_translation_empty_text_by_span": _string_counter_json(
            arabic_translation_empty_text_by_span
        ),
        "arabic_translation_zero_span_count": arabic_translation_token_counts[0],
        "arabic_translation_zero_span_examples": arabic_translation_zero_span_examples[:100],
        "first_token_not_sentence_start_count": len(first_token_not_sentence_start),
        "first_token_not_sentence_start": sorted(first_token_not_sentence_start),
        "first_sentence_after_first_token_count": len(first_sentence_after_first_token),
        "first_sentence_after_first_token": sorted(
            first_sentence_after_first_token, key=lambda item: item["source_record_id"]
        ),
        "documents_with_marker": _string_counter_json(documents_with_marker),
        "documents": documents,
    }


def render_report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = audit_upstream(args.upstream)
    rendered = render_report_json(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
