"""Deterministic, writer-independent graph construction."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Sequence

from .model import DocumentModel, LayoutEvent

NODE_TYPE_ORDER = (
    "document", "sentence", "orig_group", "norm_group", "orig",
    "page", "column", "line", "entity", "translation", "arabic_translation",
)
LAYOUT_TYPES = {"page", "column", "line"}
DOCUMENT_RELATION_TYPES = {"same_scholarly", "documented_overlap", "witness"}
OVERLAP_CLASSES = {
    "byte_identical", "core_identical_source_variant",
    "alternate_analysis", "textual_divergence",
}


@dataclass(frozen=True, slots=True)
class GraphSlot:
    id: int
    source_record_id: str
    source_word_ordinal: int
    source_id: str | None
    norm: str | None
    lemma: str | None
    pos: str | None
    func: str | None
    head_literal: str | None
    dependency_head_ordinal: int | None
    source_text: str
    kind: str = "word"


@dataclass(frozen=True, slots=True)
class GraphNode:
    id: int
    otype: str
    source_record_id: str
    source_ordinal: int | None
    slot_ranges: tuple[tuple[int, int], ...]
    value: str | None = None
    text: str | None = None
    label: str | None = None
    scholarly_id: str | None = None
    corpus: str | None = None
    dataset: str | None = None
    source_path: str | None = None
    source_sha256: str | None = None
    packaging: str | None = None
    section_address: tuple[str, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()
    metadata_duplicates: tuple[tuple[str, tuple[str, ...]], ...] = ()
    parent_node_id: int | None = None
    direct_word_slots: tuple[int, ...] = ()
    entity_class: str | None = None
    identity: str | None = None
    head_literal: str | None = None
    render_mode: str | None = None
    event_ordinal: int | None = None
    start_word_ordinal: int | None = None
    start_char: int | None = None
    start_after_word_ordinal: int | None = None
    end_word_ordinal: int | None = None
    end_char: int | None = None
    end_after_word_ordinal: int | None = None

    @property
    def slots(self) -> tuple[int, ...]:
        return tuple(
            slot
            for start, end in self.slot_ranges
            for slot in range(start, end + 1)
        )


@dataclass(frozen=True, slots=True)
class GraphEdge:
    kind: str
    source: int
    target: int
    classification: str | None = None
    family: str | None = None
    witness_literal: str | None = None
    target_scholarly_id: str | None = None


@dataclass(frozen=True, slots=True)
class NodeRange:
    otype: str
    start: int
    end: int
    count: int


@dataclass(frozen=True, slots=True)
class DocumentRelation:
    kind: str
    source_record_id: str
    target_record_id: str
    classification: str | None = None
    family: str | None = None
    witness_literal: str | None = None
    target_scholarly_id: str | None = None


@dataclass(frozen=True, slots=True)
class Graph:
    upstream_repository: str
    upstream_commit: str
    section_types: tuple[str, ...]
    slots: tuple[GraphSlot, ...]
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    node_ranges: tuple[NodeRange, ...]


def _ranges(values: Iterable[int]) -> tuple[tuple[int, int], ...]:
    items = tuple(values)
    if not items:
        return ()
    if any(value <= 0 for value in items):
        raise ValueError("graph slot ids must be positive")
    if any(right <= left for left, right in zip(items, items[1:])):
        raise ValueError("graph slot loci must be strictly increasing")
    result: list[tuple[int, int]] = []
    start = previous = items[0]
    for value in items[1:]:
        if value == previous + 1:
            previous = value
        else:
            result.append((start, previous))
            start = previous = value
    result.append((start, previous))
    return tuple(result)


def _iter_ranges(ranges: tuple[tuple[int, int], ...]):
    for start, end in ranges:
        yield from range(start, end + 1)


def _ordered_documents(documents: Sequence[DocumentModel]) -> tuple[DocumentModel, ...]:
    result = tuple(sorted(
        documents,
        key=lambda document: (document.source_record_id.casefold(), document.source_record_id),
    ))
    seen: set[str] = set()
    for document in result:
        key = document.source_record_id.casefold()
        if key in seen:
            raise ValueError(
                f"duplicate physical document source_record_id {document.source_record_id!r}"
            )
        seen.add(key)
    return result


def _check_document(document: DocumentModel):
    expected = tuple(range(1, len(document.words) + 1))
    if tuple(word.ordinal for word in document.words) != expected:
        raise ValueError(f"word ordinals are not contiguous in {document.source_record_id}")
    if not expected:
        raise ValueError(f"document has no source words in {document.source_record_id}")
    expected_set = set(expected)
    for word in document.words:
        head = word.dependency_head_ordinal
        if head not in (None, 0) and head not in expected_set:
            raise ValueError(
                f"dependency head ordinal {head} is unresolved in {document.source_record_id}"
            )

    orig_words: list[tuple[int, ...]] = []
    for index, orig in enumerate(document.origs):
        locus = tuple(orig.word_ordinals)
        if tuple(sorted(set(locus))) != locus or any(x not in expected_set for x in locus):
            raise ValueError(f"orig {index + 1} has invalid word locus in {document.source_record_id}")
        if not 0 <= orig.norm_group_index < len(document.norm_groups):
            raise ValueError(f"orig {index + 1} has invalid norm_group_index in {document.source_record_id}")
        orig_words.append(locus)

    norm_words: list[tuple[int, ...]] = []
    membership = {ordinal: 0 for ordinal in expected}
    for index, group in enumerate(document.norm_groups):
        if tuple(sorted(set(group.orig_indices))) != group.orig_indices:
            raise ValueError(f"norm_group {index + 1} has unordered orig indices in {document.source_record_id}")
        locus: set[int] = set()
        for orig_index in group.orig_indices:
            if not 0 <= orig_index < len(document.origs):
                raise ValueError(f"norm_group {index + 1} references unknown orig in {document.source_record_id}")
            if document.origs[orig_index].norm_group_index != index:
                raise ValueError(f"norm_group/orig parent mismatch in {document.source_record_id}")
            locus.update(orig_words[orig_index])
        direct = tuple(group.direct_word_ordinals)
        if tuple(sorted(set(direct))) != direct or any(x not in expected_set for x in direct):
            raise ValueError(f"norm_group {index + 1} has invalid direct-word locus in {document.source_record_id}")
        if locus.intersection(direct):
            raise ValueError(f"norm_group {index + 1} duplicates direct/orig membership in {document.source_record_id}")
        locus.update(direct)
        ordered = tuple(sorted(locus))
        norm_words.append(ordered)
        for ordinal in ordered:
            membership[ordinal] += 1
        parent = group.orig_group_index
        if parent is not None:
            if not 0 <= parent < len(document.orig_groups):
                raise ValueError(f"norm_group {index + 1} has invalid orig_group_index in {document.source_record_id}")
            if index not in document.orig_groups[parent].norm_group_indices:
                raise ValueError(f"norm_group/orig_group parent mismatch in {document.source_record_id}")
    if document.norm_groups and any(count != 1 for count in membership.values()):
        raise ValueError(f"source words must belong to exactly one norm_group in {document.source_record_id}")

    orig_group_words: list[tuple[int, ...]] = []
    for index, group in enumerate(document.orig_groups):
        if tuple(sorted(set(group.norm_group_indices))) != group.norm_group_indices:
            raise ValueError(f"orig_group {index + 1} has unordered norm_group indices in {document.source_record_id}")
        locus: set[int] = set()
        for norm_index in group.norm_group_indices:
            if not 0 <= norm_index < len(document.norm_groups):
                raise ValueError(f"orig_group {index + 1} references unknown norm_group in {document.source_record_id}")
            if document.norm_groups[norm_index].orig_group_index != index:
                raise ValueError(f"orig_group/norm_group parent mismatch in {document.source_record_id}")
            locus.update(norm_words[norm_index])
        orig_group_words.append(tuple(sorted(locus)))

    sentence_membership = {ordinal: 0 for ordinal in expected}
    for sentence in document.sentences:
        locus = tuple(sentence.word_ordinals)
        if tuple(sorted(set(locus))) != locus or any(x not in expected_set for x in locus):
            raise ValueError(f"sentence {sentence.ordinal} has invalid word locus in {document.source_record_id}")
        for ordinal in locus:
            sentence_membership[ordinal] += 1
    if any(count != 1 for count in sentence_membership.values()):
        raise ValueError(f"source words must belong to exactly one sentence in {document.source_record_id}")
    return tuple(norm_words), tuple(orig_group_words)


def _boundary(document: DocumentModel, event: LayoutEvent) -> tuple[int, int]:
    word_count = len(document.words)
    if event.word_ordinal is not None:
        if not 1 <= event.word_ordinal <= word_count or event.char_offset is None:
            raise ValueError(f"layout event {event.ordinal} has invalid word position in {document.source_record_id}")
        word = document.words[event.word_ordinal - 1]
        if not 0 <= event.char_offset <= len(word.source_text):
            raise ValueError(f"layout event {event.ordinal} char offset is outside word in {document.source_record_id}")
        if event.after_word_ordinal != event.word_ordinal - 1:
            raise ValueError(f"layout event {event.ordinal} has inconsistent after_word_ordinal in {document.source_record_id}")
        return event.word_ordinal, event.char_offset
    if event.char_offset is not None or not 0 <= event.after_word_ordinal <= word_count:
        raise ValueError(f"layout event {event.ordinal} has invalid inter-word position in {document.source_record_id}")
    return event.after_word_ordinal + 1, 0


def _layout_segment(document, event, next_event, slot_lookup):
    start = _boundary(document, event)
    end = _boundary(document, next_event) if next_event else (len(document.words) + 1, 0)
    if end < start:
        raise ValueError(f"layout events are out of source order in {document.source_record_id}")
    slots: list[int] = []
    text: list[str] = []
    for ordinal in range(start[0], min(end[0], len(document.words)) + 1):
        source_text = document.words[ordinal - 1].source_text
        lo = start[1] if ordinal == start[0] else 0
        hi = end[1] if ordinal == end[0] else len(source_text)
        if ordinal == end[0] and end[1] == 0:
            hi = 0
        if hi > lo:
            slots.append(slot_lookup[(document.source_record_id, ordinal)])
            text.append(source_text[lo:hi])
    return tuple(slots), "".join(text), start, end


def build_graph(
    documents: Sequence[DocumentModel],
    *,
    document_relations: Sequence[DocumentRelation] = (),
) -> Graph:
    ordered = _ordered_documents(documents)
    if not ordered:
        raise ValueError("cannot build graph without documents")
    repositories = {document.upstream_repository for document in ordered}
    commits = {document.upstream_commit for document in ordered}
    if len(repositories) != 1 or len(commits) != 1:
        raise ValueError("all documents must come from one exact upstream repository revision")

    norm_words: dict[str, tuple[tuple[int, ...], ...]] = {}
    orig_group_words: dict[str, tuple[tuple[int, ...], ...]] = {}
    slots: list[GraphSlot] = []
    slot_lookup: dict[tuple[str, int], int] = {}
    for document in ordered:
        norm_words[document.source_record_id], orig_group_words[document.source_record_id] = _check_document(document)
        for word in document.words:
            slot_id = len(slots) + 1
            slot_lookup[(document.source_record_id, word.ordinal)] = slot_id
            slots.append(GraphSlot(
                slot_id, document.source_record_id, word.ordinal, word.source_id,
                word.norm, word.lemma, word.pos, word.func, word.head_literal,
                word.dependency_head_ordinal, word.source_text,
            ))

    def gslots(document: DocumentModel, ordinals: Iterable[int]) -> tuple[int, ...]:
        return tuple(slot_lookup[(document.source_record_id, ordinal)] for ordinal in ordinals)

    nodes: list[GraphNode] = []
    node_ranges: list[NodeRange] = []
    document_ids: dict[str, int] = {}
    orig_group_ids: dict[tuple[str, int], int] = {}
    norm_group_ids: dict[tuple[str, int], int] = {}
    entity_ids: dict[tuple[str, int], int] = {}
    entity_heads: list[tuple[int, str, int]] = []

    def add(otype: str, **kwargs) -> GraphNode:
        node = GraphNode(len(slots) + len(nodes) + 1, otype, **kwargs)
        nodes.append(node)
        return node

    for otype in NODE_TYPE_ORDER:
        range_start = len(slots) + len(nodes) + 1
        before = len(nodes)
        for document in ordered:
            record = document.source_record_id
            if otype == "document":
                node = add(
                    otype, source_record_id=record, source_ordinal=None,
                    slot_ranges=_ranges(gslots(document, range(1, len(document.words) + 1))),
                    scholarly_id=document.scholarly_id, corpus=document.corpus,
                    dataset=document.dataset, source_path=document.source_path,
                    source_sha256=document.source_sha256, packaging=document.packaging,
                    section_address=(record,),
                    metadata=tuple(sorted(document.metadata.items())),
                    metadata_duplicates=tuple(sorted(document.metadata_duplicates.items())),
                )
                document_ids[record] = node.id
            elif otype == "sentence":
                for item in sorted(document.sentences, key=lambda x: x.ordinal):
                    add(otype, source_record_id=record, source_ordinal=item.ordinal,
                        slot_ranges=_ranges(gslots(document, item.word_ordinals)))
            elif otype == "orig_group":
                for index, item in enumerate(document.orig_groups):
                    node = add(otype, source_record_id=record, source_ordinal=index + 1,
                        slot_ranges=_ranges(gslots(document, orig_group_words[record][index])),
                        value=item.value)
                    orig_group_ids[(record, index)] = node.id
            elif otype == "norm_group":
                for index, item in enumerate(document.norm_groups):
                    parent = None if item.orig_group_index is None else orig_group_ids[(record, item.orig_group_index)]
                    node = add(otype, source_record_id=record, source_ordinal=index + 1,
                        slot_ranges=_ranges(gslots(document, norm_words[record][index])),
                        value=item.value, parent_node_id=parent,
                        direct_word_slots=gslots(document, item.direct_word_ordinals))
                    norm_group_ids[(record, index)] = node.id
            elif otype == "orig":
                for index, item in enumerate(document.origs):
                    add(otype, source_record_id=record, source_ordinal=index + 1,
                        slot_ranges=_ranges(gslots(document, item.word_ordinals)), value=item.value,
                        parent_node_id=norm_group_ids[(record, item.norm_group_index)])
            elif otype in LAYOUT_TYPES:
                events = sorted(
                    (event for event in document.layout_events if event.kind == otype),
                    key=lambda event: event.ordinal,
                )
                for index, event in enumerate(events):
                    next_event = events[index + 1] if index + 1 < len(events) else None
                    locus, text, start, end = _layout_segment(document, event, next_event, slot_lookup)
                    add(
                        otype, source_record_id=record, source_ordinal=event.ordinal,
                        slot_ranges=_ranges(locus), text=text, label=event.value,
                        render_mode="own_text", event_ordinal=event.ordinal,
                        start_word_ordinal=event.word_ordinal, start_char=event.char_offset,
                        start_after_word_ordinal=event.after_word_ordinal,
                        end_word_ordinal=next_event.word_ordinal if next_event else None,
                        end_char=next_event.char_offset if next_event else None,
                        end_after_word_ordinal=next_event.after_word_ordinal if next_event else len(document.words),
                    )
            elif otype == "entity":
                for item in sorted(document.entities, key=lambda x: x.ordinal):
                    if not item.word_ordinals:
                        raise ValueError(f"entity has no word locus in {record}")
                    if item.head_word_ordinal not in item.word_ordinals:
                        raise ValueError(f"entity head {item.head_literal!r} is outside entity word locus in {record}")
                    parent = None
                    if item.parent_entity_ordinal is not None:
                        parent = entity_ids.get((record, item.parent_entity_ordinal))
                        if parent is None:
                            raise ValueError(f"entity parent is unresolved in {record}")
                    node = add(
                        otype, source_record_id=record, source_ordinal=item.ordinal,
                        slot_ranges=_ranges(gslots(document, item.word_ordinals)),
                        parent_node_id=parent, entity_class=item.entity_class,
                        identity=item.identity, head_literal=item.head_literal,
                    )
                    entity_ids[(record, item.ordinal)] = node.id
                    entity_heads.append((node.id, record, item.head_word_ordinal))
            elif otype in {"translation", "arabic_translation"}:
                items = document.translations if otype == "translation" else document.arabic_translations
                for item in sorted(items, key=lambda x: x.ordinal):
                    if not item.word_ordinals:
                        raise ValueError(f"{otype} has no word locus in {record}")
                    add(otype, source_record_id=record, source_ordinal=item.ordinal,
                        slot_ranges=_ranges(gslots(document, item.word_ordinals)),
                        text=item.text, render_mode="own_text")
        count = len(nodes) - before
        if count:
            node_ranges.append(NodeRange(otype, range_start, range_start + count - 1, count))

    edges: list[GraphEdge] = []
    for slot in slots:
        head = slot.dependency_head_ordinal
        if head not in (None, 0):
            target = slot_lookup.get((slot.source_record_id, head))
            if target is None:
                raise ValueError(f"dependency head ordinal {head} is unresolved in {slot.source_record_id}")
            edges.append(GraphEdge("dependency_head", slot.id, target))
    for entity_id, record, head in entity_heads:
        edges.append(GraphEdge("entity_head", entity_id, slot_lookup[(record, head)]))

    document_nodes = {node.source_record_id: node for node in nodes if node.otype == "document"}
    for relation in sorted(document_relations, key=lambda item: (
        item.kind, item.source_record_id.casefold(), item.source_record_id,
        item.target_record_id.casefold(), item.target_record_id,
        item.classification or "", item.family or "", item.witness_literal or "",
        item.target_scholarly_id or "",
    )):
        if relation.kind not in DOCUMENT_RELATION_TYPES:
            raise ValueError(f"unsupported document relation kind {relation.kind!r}")
        source = document_nodes.get(relation.source_record_id)
        target = document_nodes.get(relation.target_record_id)
        if source is None or target is None:
            raise ValueError(f"document relation {relation.kind!r} references unknown physical document")
        if relation.kind in {"same_scholarly", "documented_overlap"}:
            if relation.classification not in OVERLAP_CLASSES:
                raise ValueError(f"document relation {relation.kind!r} requires measured classification")
            if relation.kind == "same_scholarly":
                if not source.scholarly_id or source.scholarly_id != target.scholarly_id:
                    raise ValueError("same_scholarly relation requires matching scholarly identities")
            elif not relation.family:
                raise ValueError("documented_overlap relation requires relation family")
        else:
            if not relation.witness_literal or not relation.target_scholarly_id:
                raise ValueError("witness relation requires literal witness and target scholarly identity")
            if target.scholarly_id != relation.target_scholarly_id:
                raise ValueError("witness target scholarly identity does not match target document")
        edges.append(GraphEdge(
            relation.kind, source.id, target.id, relation.classification,
            relation.family, relation.witness_literal, relation.target_scholarly_id,
        ))

    edges.sort(key=lambda edge: (
        edge.kind, edge.source, edge.target, edge.classification or "",
        edge.family or "", edge.witness_literal or "", edge.target_scholarly_id or "",
    ))
    graph = Graph(
        next(iter(repositories)), next(iter(commits)), ("document",),
        tuple(slots), tuple(nodes), tuple(edges), tuple(node_ranges),
    )
    errors = validate_graph(graph)
    if errors:
        raise ValueError("graph validation failed: " + "; ".join(errors[:8]))
    return graph


def validate_graph(graph: Graph) -> tuple[str, ...]:
    errors: list[str] = []
    if not graph.upstream_repository or not graph.upstream_commit:
        errors.append("graph provenance requires upstream repository and commit")
    if graph.section_types != ("document",):
        errors.append("section hierarchy must be document-only")
    slot_by_id = {slot.id: slot for slot in graph.slots}
    if tuple(slot_by_id) != tuple(range(1, len(graph.slots) + 1)):
        errors.append("slot ids are not contiguous from 1")
    if any(slot.kind != "word" for slot in graph.slots):
        errors.append("graph contains non-word/synthetic slot")

    node_by_id = {node.id: node for node in graph.nodes}
    expected_node_ids = range(len(graph.slots) + 1, len(graph.slots) + len(graph.nodes) + 1)
    if tuple(node_by_id) != tuple(expected_node_ids):
        errors.append("non-slot node ids are not contiguous after slots")
    nodes_by_type: dict[str, list[GraphNode]] = {otype: [] for otype in NODE_TYPE_ORDER}
    for node in graph.nodes:
        nodes_by_type.setdefault(node.otype, []).append(node)
        for start, end in node.slot_ranges:
            if start > end or start not in slot_by_id or end not in slot_by_id:
                errors.append(f"node {node.id} has invalid slot range")

    range_by_type = {item.otype: item for item in graph.node_ranges}
    cursor = len(graph.slots) + 1
    for otype in NODE_TYPE_ORDER:
        typed = nodes_by_type.get(otype, [])
        if not typed:
            continue
        declared = range_by_type.get(otype)
        if declared is None:
            errors.append(f"missing node range for {otype}")
            continue
        if (declared.start, declared.end, declared.count) != (
            cursor, cursor + len(typed) - 1, len(typed)
        ):
            errors.append(f"node range for {otype} is not contiguous")
        if typed[0].id != declared.start or typed[-1].id != declared.end:
            errors.append(f"node ids for {otype} do not occupy their declared range")
        cursor = declared.end + 1
    if cursor != len(graph.slots) + len(graph.nodes) + 1:
        errors.append("node ranges do not cover every non-slot node")

    documents = nodes_by_type.get("document", [])
    document_by_record: dict[str, GraphNode] = {}
    slot_document: dict[int, int] = {}
    for document in documents:
        if document.source_record_id in document_by_record:
            errors.append(f"duplicate physical document {document.source_record_id}")
        document_by_record[document.source_record_id] = document
        if document.section_address != (document.source_record_id,):
            errors.append(f"document {document.id} has invalid section address")
        for slot_id in _iter_ranges(document.slot_ranges):
            if slot_id in slot_document:
                errors.append(f"slot {slot_id} belongs to multiple documents")
            slot_document[slot_id] = document.id
    for slot in graph.slots:
        owner = document_by_record.get(slot.source_record_id)
        if owner is None or slot_document.get(slot.id) != owner.id:
            errors.append(f"slot {slot.id} document/source_record mismatch")

    sentence_membership = [0] * (len(graph.slots) + 1)
    for sentence in nodes_by_type.get("sentence", []):
        owner = document_by_record.get(sentence.source_record_id)
        for slot_id in _iter_ranges(sentence.slot_ranges):
            sentence_membership[slot_id] += 1
            if owner is None or slot_document.get(slot_id) != owner.id:
                errors.append(f"sentence {sentence.id} crosses physical documents")
    for slot in graph.slots:
        if sentence_membership[slot.id] != 1:
            errors.append(
                f"slot {slot.id} must belong to exactly one sentence; found {sentence_membership[slot.id]}"
            )

    for node in graph.nodes:
        if node.otype == "document":
            continue
        owner = document_by_record.get(node.source_record_id)
        if owner is None:
            errors.append(f"node {node.id} references unknown source record")
            continue
        for slot_id in _iter_ranges(node.slot_ranges):
            if slot_document.get(slot_id) != owner.id:
                errors.append(f"{node.otype} node {node.id} crosses physical documents")
        if node.otype in {"translation", "arabic_translation"}:
            if not node.slot_ranges:
                errors.append(f"{node.otype} node {node.id} lacks measured word locus")
            if node.render_mode != "own_text" or node.text is None:
                errors.append(f"{node.otype} node {node.id} must render own text")
        if node.otype in LAYOUT_TYPES and (node.render_mode != "own_text" or node.text is None):
            errors.append(f"layout node {node.id} must render own text")
        if node.otype == "norm_group":
            if node.parent_node_id is not None:
                parent = node_by_id.get(node.parent_node_id)
                if parent is None or parent.otype != "orig_group" or parent.source_record_id != node.source_record_id:
                    errors.append(f"norm_group node {node.id} has invalid orig_group parent")
            locus = set(_iter_ranges(node.slot_ranges))
            if any(slot_id not in locus for slot_id in node.direct_word_slots):
                errors.append(f"norm_group node {node.id} direct words escape its locus")
        if node.otype == "orig":
            parent = node_by_id.get(node.parent_node_id) if node.parent_node_id else None
            if parent is None or parent.otype != "norm_group" or parent.source_record_id != node.source_record_id:
                errors.append(f"orig node {node.id} has invalid norm_group parent")
        if node.otype == "entity" and node.parent_node_id is not None:
            parent = node_by_id.get(node.parent_node_id)
            if parent is None or parent.otype != "entity" or parent.source_record_id != node.source_record_id:
                errors.append(f"entity node {node.id} has invalid parent entity")

    for edge in graph.edges:
        if edge.kind == "dependency_head":
            source = slot_by_id.get(edge.source)
            target = slot_by_id.get(edge.target)
            if source is None or target is None:
                errors.append(f"dependency edge {edge.source}->{edge.target} must connect word slots")
            elif source.source_record_id != target.source_record_id:
                errors.append(f"dependency edge {edge.source}->{edge.target} crosses documents")
        elif edge.kind == "entity_head":
            source = node_by_id.get(edge.source)
            target = slot_by_id.get(edge.target)
            if source is None or source.otype != "entity" or target is None:
                errors.append(f"entity_head edge {edge.source}->{edge.target} has invalid endpoints")
            elif edge.target not in set(_iter_ranges(source.slot_ranges)):
                errors.append(f"entity_head edge {edge.source}->{edge.target} lies outside entity locus")
            elif source.source_record_id != target.source_record_id:
                errors.append(f"entity_head edge {edge.source}->{edge.target} crosses documents")
        elif edge.kind in DOCUMENT_RELATION_TYPES:
            source = node_by_id.get(edge.source)
            target = node_by_id.get(edge.target)
            if source is None or target is None or source.otype != "document" or target.otype != "document":
                errors.append(f"{edge.kind} edge must connect document nodes")
            elif edge.kind in {"same_scholarly", "documented_overlap"} and edge.classification not in OVERLAP_CLASSES:
                errors.append(f"{edge.kind} edge lacks measured classification")
            elif edge.kind == "same_scholarly" and (not source.scholarly_id or source.scholarly_id != target.scholarly_id):
                errors.append("same_scholarly edge connects different scholarly identities")
            elif edge.kind == "documented_overlap" and not edge.family:
                errors.append("documented_overlap edge lacks family")
            elif edge.kind == "witness":
                if not edge.witness_literal or not edge.target_scholarly_id:
                    errors.append("witness edge lacks literal/target evidence")
                elif target.scholarly_id != edge.target_scholarly_id:
                    errors.append("witness edge target scholarly identity mismatch")
        else:
            errors.append(f"unsupported graph edge kind {edge.kind!r}")
    return tuple(errors)


def graph_fingerprint(graph: Graph) -> str:
    digest = sha256()
    def emit(*values: object) -> None:
        digest.update(repr(values).encode("utf-8"))
        digest.update(b"\n")
    emit("provenance", graph.upstream_repository, graph.upstream_commit, graph.section_types)
    for slot in graph.slots:
        emit("slot", slot.id, slot.kind, slot.source_record_id, slot.source_word_ordinal,
             slot.source_id, slot.norm, slot.lemma, slot.pos, slot.func, slot.head_literal,
             slot.dependency_head_ordinal, slot.source_text)
    for node in graph.nodes:
        emit("node", node.id, node.otype, node.source_record_id, node.source_ordinal,
             node.slot_ranges, node.value, node.text, node.label, node.scholarly_id,
             node.corpus, node.dataset, node.source_path, node.source_sha256, node.packaging,
             node.section_address, node.metadata, node.metadata_duplicates, node.parent_node_id,
             node.direct_word_slots, node.entity_class, node.identity, node.head_literal,
             node.render_mode, node.event_ordinal, node.start_word_ordinal, node.start_char,
             node.start_after_word_ordinal, node.end_word_ordinal, node.end_char,
             node.end_after_word_ordinal)
    for edge in graph.edges:
        emit("edge", edge.kind, edge.source, edge.target, edge.classification, edge.family,
             edge.witness_literal, edge.target_scholarly_id)
    for item in graph.node_ranges:
        emit("range", item.otype, item.start, item.end, item.count)
    return digest.hexdigest()
