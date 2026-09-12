"""Deterministic event-driven parser for Coptic Scriptorium TT sources."""

from __future__ import annotations

from hashlib import sha256
import html
from pathlib import Path
import re
from typing import Any
import zipfile

from .model import (
    DocumentModel,
    Entity,
    LayoutEvent,
    NormGroup,
    Orig,
    OrigGroup,
    Sentence,
    Translation,
    Word,
)


TAG_RE = re.compile(r"<(/?)([A-Za-z_][A-Za-z0-9_.:-]*)([^>]*)>")
ATTR_RE = re.compile(r'\s+([A-Za-z_][A-Za-z0-9_.:-]*)\s*=\s*"([^"]*)"')
LAYOUT_TAGS = {
    "pb_xml_id": ("page", "pb_xml_id"),
    "cb_n": ("column", "cb_n"),
    "lb_n": ("line", "lb_n"),
}


def _scan_attrs(fragment: str, *, allow_duplicates: bool = False) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    position = 0
    values: dict[str, list[str]] = {}
    while position < len(fragment):
        if not fragment[position:].strip():
            break
        match = ATTR_RE.match(fragment, position)
        if match is None:
            raise ValueError(f"malformed tag attributes near offset {position}")
        name = match.group(1)
        value = html.unescape(match.group(2))
        values.setdefault(name, []).append(value)
        position = match.end()
    duplicates = {
        name: tuple(items)
        for name, items in sorted(values.items())
        if len(items) > 1
    }
    if duplicates and not allow_duplicates:
        first = next(iter(duplicates))
        raise ValueError(f"duplicate tag attribute {first!r}")
    attrs = {name: items[0] for name, items in values.items()}
    return attrs, duplicates


def _visible_piece(value: str) -> str:
    return "".join(character for character in html.unescape(value) if not character.isspace())


def _append_unique(values: list[int], value: int) -> None:
    if not values or values[-1] != value:
        values.append(value)


def parse_tt_record(
    raw: bytes,
    *,
    source_record_id: str,
    source_path: str,
    upstream_repository: str,
    upstream_commit: str,
    packaging: str = "directory",
) -> DocumentModel:
    """Parse one strict-UTF-8 TT record into the TF-independent source model."""

    text = raw.decode("utf-8")
    if not text.strip():
        raise ValueError(f"empty TT source record {source_record_id}")

    try:
        prefix, record = source_record_id.split(":", 1)
        corpus, dataset = prefix.split("/", 1)
        if not corpus or not dataset or not record:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"invalid source_record_id {source_record_id!r}") from exc

    metadata_view = text[1:] if text.startswith("\ufeff") else text
    first_tag = TAG_RE.search(metadata_view)
    if (
        first_tag is None
        or first_tag.group(1)
        or first_tag.group(2) != "meta"
        or metadata_view[: first_tag.start()].strip()
    ):
        raise ValueError(f"TT record {source_record_id} does not start with metadata")
    metadata, metadata_duplicates = _scan_attrs(first_tag.group(3), allow_duplicates=True)

    raw_words: list[dict[str, Any]] = []
    source_id_to_ordinal: dict[str, int] = {}
    sentence_starts: list[int] = []

    orig_groups_raw: list[dict[str, Any]] = []
    norm_groups_raw: list[dict[str, Any]] = []
    origs_raw: list[dict[str, Any]] = []
    orig_group_stack: list[int] = []
    norm_group_stack: list[int] = []
    orig_stack: list[int] = []
    linguistic_stack: list[str] = []

    entities_raw: list[dict[str, Any]] = []
    entity_stack: list[dict[str, Any]] = []
    entity_open_count = 0
    translations_raw: list[dict[str, Any]] = []
    translation_stack: list[dict[str, Any]] = []
    arabic_raw: list[dict[str, Any]] = []
    arabic_stack: list[dict[str, Any]] = []
    layout_events: list[LayoutEvent] = []
    current_word: dict[str, Any] | None = None

    def append_word_text(fragment: str) -> None:
        if current_word is None:
            return
        piece = _visible_piece(fragment)
        if piece:
            current_word["text_parts"].append(piece)

    def current_offset() -> int:
        if current_word is None:
            return 0
        return sum(len(piece) for piece in current_word["text_parts"])

    def close_linguistic(name: str) -> None:
        if not linguistic_stack or linguistic_stack[-1] != name:
            actual = linguistic_stack[-1] if linguistic_stack else None
            raise ValueError(
                f"linguistic tag order violation in {source_record_id}: "
                f"closing {name!r} while {actual!r} is open"
            )
        linguistic_stack.pop()

    cursor = 0
    for match in TAG_RE.finditer(text):
        append_word_text(text[cursor : match.start()])
        cursor = match.end()
        closing = bool(match.group(1))
        name = match.group(2)
        attrs: dict[str, str]
        if closing or name == "meta":
            attrs = {}
        else:
            attrs, _ = _scan_attrs(match.group(3))

        if closing:
            if name == "norm":
                if current_word is None:
                    raise ValueError(f"closing norm without open norm in {source_record_id}")
                close_linguistic("norm")
                current_word["source_text"] = "".join(current_word["text_parts"])
                raw_words.append(current_word)
                current_word = None
            elif name == "orig":
                if not orig_stack:
                    raise ValueError(f"closing orig without open orig in {source_record_id}")
                close_linguistic("orig")
                orig_stack.pop()
            elif name == "norm_group":
                if not norm_group_stack:
                    raise ValueError(f"closing norm_group without open norm_group in {source_record_id}")
                close_linguistic("norm_group")
                norm_group_stack.pop()
            elif name == "orig_group":
                if not orig_group_stack:
                    raise ValueError(f"closing orig_group without open orig_group in {source_record_id}")
                close_linguistic("orig_group")
                orig_group_stack.pop()
            elif name == "entity":
                if not entity_stack:
                    raise ValueError(f"closing entity without open entity in {source_record_id}")
                entities_raw.append(entity_stack.pop())
            elif name == "translation":
                if not translation_stack:
                    raise ValueError(f"closing translation without open translation in {source_record_id}")
                translations_raw.append(translation_stack.pop())
            elif name in {"arabic", "arabic_translation"}:
                if not arabic_stack:
                    raise ValueError(f"closing Arabic translation without open annotation in {source_record_id}")
                arabic_raw.append(arabic_stack.pop())
            continue

        if name == "meta":
            continue
        if name == "orig_group":
            index = len(orig_groups_raw)
            orig_groups_raw.append({"value": attrs.get("orig_group"), "norm_group_indices": []})
            orig_group_stack.append(index)
            linguistic_stack.append("orig_group")
        elif name == "norm_group":
            index = len(norm_groups_raw)
            parent = orig_group_stack[-1] if orig_group_stack else None
            norm_groups_raw.append(
                {
                    "value": attrs.get("norm_group"),
                    "orig_indices": [],
                    "direct_word_ordinals": [],
                    "orig_group_index": parent,
                }
            )
            if parent is not None:
                orig_groups_raw[parent]["norm_group_indices"].append(index)
            norm_group_stack.append(index)
            linguistic_stack.append("norm_group")
        elif name == "orig":
            if not norm_group_stack:
                raise ValueError(f"orig outside norm_group in {source_record_id}")
            index = len(origs_raw)
            parent = norm_group_stack[-1]
            origs_raw.append(
                {
                    "value": attrs.get("orig"),
                    "word_ordinals": [],
                    "norm_group_index": parent,
                }
            )
            norm_groups_raw[parent]["orig_indices"].append(index)
            orig_stack.append(index)
            linguistic_stack.append("orig")
        elif name == "norm":
            if current_word is not None:
                raise ValueError(f"nested norm tags in {source_record_id}")
            if not norm_group_stack:
                raise ValueError(f"norm outside norm_group in {source_record_id}")
            ordinal = len(raw_words) + 1
            source_id = attrs.get("xml:id")
            if source_id:
                if source_id in source_id_to_ordinal:
                    raise ValueError(f"duplicate source word id {source_id!r} in {source_record_id}")
                source_id_to_ordinal[source_id] = ordinal
            current_word = {
                "ordinal": ordinal,
                "source_id": source_id,
                "norm": attrs.get("norm"),
                "lemma": attrs.get("lemma"),
                "pos": attrs.get("pos"),
                "func": attrs.get("func"),
                "head_literal": attrs.get("head"),
                "text_parts": [],
                "source_text": "",
            }
            linguistic_stack.append("norm")
            if (attrs.get("new_sent") or "").casefold() == "true":
                sentence_starts.append(ordinal)
            if orig_stack:
                origs_raw[orig_stack[-1]]["word_ordinals"].append(ordinal)
            else:
                norm_groups_raw[norm_group_stack[-1]]["direct_word_ordinals"].append(ordinal)
            for entity in entity_stack:
                _append_unique(entity["word_ordinals"], ordinal)
            for translation in translation_stack:
                _append_unique(translation["word_ordinals"], ordinal)
            for translation in arabic_stack:
                _append_unique(translation["word_ordinals"], ordinal)
        elif name in LAYOUT_TAGS:
            kind, attr_name = LAYOUT_TAGS[name]
            layout_events.append(
                LayoutEvent(
                    ordinal=len(layout_events) + 1,
                    kind=kind,
                    value=attrs.get(attr_name),
                    word_ordinal=current_word["ordinal"] if current_word else None,
                    char_offset=current_offset() if current_word else None,
                )
            )
        elif name == "entity":
            entity_open_count += 1
            locus: list[int] = []
            if current_word is not None:
                locus.append(current_word["ordinal"])
            entity_stack.append(
                {
                    "ordinal": entity_open_count,
                    "parent_entity_ordinal": entity_stack[-1]["ordinal"] if entity_stack else None,
                    "entity_class": attrs.get("entity"),
                    "identity": attrs.get("identity"),
                    "head_literal": attrs.get("head_tok"),
                    "word_ordinals": locus,
                }
            )
        elif name == "translation":
            locus: list[int] = []
            if current_word is not None:
                locus.append(current_word["ordinal"])
            translation_stack.append(
                {"text": attrs.get("translation") or "", "word_ordinals": locus}
            )
        elif name in {"arabic", "arabic_translation"}:
            locus: list[int] = []
            if current_word is not None:
                locus.append(current_word["ordinal"])
            arabic_stack.append(
                {
                    "text": attrs.get("arabic") or attrs.get("arabic_translation") or "",
                    "word_ordinals": locus,
                }
            )

    append_word_text(text[cursor:])
    if current_word is not None:
        raise ValueError(f"unclosed norm in {source_record_id}")
    if orig_stack or norm_group_stack or orig_group_stack or linguistic_stack:
        raise ValueError(f"unclosed linguistic grouping tag in {source_record_id}")
    if entity_stack:
        raise ValueError(f"unclosed entity tag in {source_record_id}")
    if translation_stack:
        raise ValueError(f"unclosed translation tag in {source_record_id}")
    if arabic_stack:
        raise ValueError(f"unclosed Arabic translation tag in {source_record_id}")

    if raw_words and (not sentence_starts or sentence_starts[0] != 1):
        raise ValueError(f"first word has no source sentence start in {source_record_id}")

    words: list[Word] = []
    for raw_word in raw_words:
        literal_head = raw_word["head_literal"]
        func = raw_word["func"]
        if literal_head:
            target = literal_head[1:] if literal_head.startswith("#") else literal_head
            if target not in source_id_to_ordinal:
                raise ValueError(f"dependency head {literal_head!r} is unresolved in {source_record_id}")
            dependency_head = source_id_to_ordinal[target]
        elif func == "root":
            dependency_head = 0
        else:
            dependency_head = None
        words.append(
            Word(
                ordinal=raw_word["ordinal"],
                source_id=raw_word["source_id"],
                norm=raw_word["norm"],
                lemma=raw_word["lemma"],
                pos=raw_word["pos"],
                func=func,
                head_literal=literal_head,
                dependency_head_ordinal=dependency_head,
                source_text=raw_word["source_text"],
            )
        )

    sentences: list[Sentence] = []
    for index, start in enumerate(sentence_starts):
        end = sentence_starts[index + 1] - 1 if index + 1 < len(sentence_starts) else len(words)
        sentences.append(Sentence(index + 1, tuple(range(start, end + 1))))

    entities: list[Entity] = []
    for raw_entity in sorted(entities_raw, key=lambda item: item["ordinal"]):
        head_literal = raw_entity["head_literal"]
        if not head_literal:
            raise ValueError(f"entity head is missing in {source_record_id}")
        target = head_literal[1:] if head_literal.startswith("#") else head_literal
        if target not in source_id_to_ordinal:
            raise ValueError(f"entity head {head_literal!r} is unresolved in {source_record_id}")
        head_ordinal = source_id_to_ordinal[target]
        locus = tuple(raw_entity["word_ordinals"])
        if head_ordinal not in locus:
            raise ValueError(f"entity head {head_literal!r} is outside corrected entity locus in {source_record_id}")
        if not locus:
            raise ValueError(f"entity has no word locus in {source_record_id}")
        entities.append(
            Entity(
                ordinal=raw_entity["ordinal"],
                parent_entity_ordinal=raw_entity["parent_entity_ordinal"],
                entity_class=raw_entity["entity_class"],
                identity=raw_entity["identity"],
                head_literal=head_literal,
                head_word_ordinal=head_ordinal,
                word_ordinals=locus,
            )
        )

    def freeze_translations(raw_items: list[dict[str, Any]]) -> tuple[Translation, ...]:
        result: list[Translation] = []
        for raw_item in raw_items:
            locus = tuple(raw_item["word_ordinals"])
            if not locus:
                raise ValueError(f"translation has no word locus in {source_record_id}")
            result.append(Translation(len(result) + 1, raw_item["text"], locus))
        return tuple(result)

    origs = tuple(
        Orig(item["value"], tuple(item["word_ordinals"]), item["norm_group_index"])
        for item in origs_raw
    )
    norm_groups = tuple(
        NormGroup(
            item["value"],
            tuple(item["orig_indices"]),
            tuple(item["direct_word_ordinals"]),
            item["orig_group_index"],
        )
        for item in norm_groups_raw
    )
    orig_groups = tuple(
        OrigGroup(item["value"], tuple(item["norm_group_indices"]))
        for item in orig_groups_raw
    )

    return DocumentModel(
        source_record_id=source_record_id,
        source_path=source_path,
        source_sha256=sha256(raw).hexdigest(),
        packaging=packaging,
        upstream_repository=upstream_repository,
        upstream_commit=upstream_commit,
        corpus=corpus,
        dataset=dataset,
        record=record,
        scholarly_id=(metadata.get("document_cts_urn") or "").strip() or None,
        metadata=dict(metadata),
        metadata_duplicates=dict(metadata_duplicates),
        words=tuple(words),
        sentences=tuple(sentences),
        origs=origs,
        norm_groups=norm_groups,
        orig_groups=orig_groups,
        layout_events=tuple(layout_events),
        entities=tuple(entities),
        translations=freeze_translations(translations_raw),
        arabic_translations=freeze_translations(arabic_raw),
        source_text=text,
    )


def _source_record_id(corpus: str, dataset: str, record: str) -> str:
    return f"{corpus}/{dataset}:{record}"


def parse_source_tree(
    root: Path | str,
    *,
    upstream_repository: str,
    upstream_commit: str,
) -> list[DocumentModel]:
    """Discover and parse supported TT records in deterministic physical order."""

    root_path = Path(root)
    pending: list[tuple[str, str, bytes, str]] = []

    for directory in sorted(
        (path for path in root_path.rglob("*_TT") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        relative = directory.relative_to(root_path)
        if len(relative.parts) != 2 or not relative.parts[1].endswith("_TT"):
            raise ValueError(f"unsupported TT dataset layout: {relative.as_posix()!r}")
        corpus = relative.parts[0]
        dataset = relative.parts[1][:-3]
        for path in sorted(
            (item for item in directory.rglob("*") if item.is_file() and item.suffix.casefold() == ".tt"),
            key=lambda item: item.as_posix(),
        ):
            logical_path = path.relative_to(directory)
            if len(logical_path.parts) != 1:
                raise ValueError(
                    f"unsupported TT directory member layout in {relative.as_posix()}: "
                    f"{logical_path.as_posix()!r}"
                )
            logical = logical_path.as_posix()
            record = logical[: -len(path.suffix)]
            source_id = _source_record_id(corpus, dataset, record)
            pending.append((source_id, path.relative_to(root_path).as_posix(), path.read_bytes(), "directory"))

    for archive_path in sorted(root_path.rglob("*_TT.zip"), key=lambda path: path.as_posix()):
        relative = archive_path.relative_to(root_path)
        if len(relative.parts) != 2 or not relative.parts[1].endswith("_TT.zip"):
            raise ValueError(f"unsupported TT dataset layout: {relative.as_posix()!r}")
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
                    if not logical or "/" in logical:
                        raise ValueError(
                            f"unsupported TT archive member layout in {relative.as_posix()}: {member!r}"
                        )
                else:
                    raise ValueError(f"unsupported TT archive member layout in {relative.as_posix()}: {member!r}")
                record = logical[:-3]
                source_id = _source_record_id(corpus, dataset, record)
                pending.append((source_id, f"{relative.as_posix()}!/{member}", archive.read(member), "archive"))

    pending.sort(key=lambda item: (item[0].casefold(), item[0]))
    seen: dict[str, str] = {}
    documents: list[DocumentModel] = []
    for source_id, source_path, raw, packaging in pending:
        technical = source_id.casefold()
        previous = seen.get(technical)
        if previous is not None:
            raise ValueError(f"source-record collision: {previous!r} versus {source_id!r}")
        seen[technical] = source_id
        documents.append(
            parse_tt_record(
                raw,
                source_record_id=source_id,
                source_path=source_path,
                upstream_repository=upstream_repository,
                upstream_commit=upstream_commit,
                packaging=packaging,
            )
        )
    return documents