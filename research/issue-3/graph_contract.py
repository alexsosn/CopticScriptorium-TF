"""Synthetic graph-contract validator for CopticScriptorium-TF issue #3.

This module validates research fixtures for the proposed intermediate graph. It is
not a Text-Fabric writer. The contract exists so later implementation tickets have
machine-testable invariants derived from the corpus-wide research evidence.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


LAYOUT_TYPES = {"page", "column", "line"}
TEXTUAL_ZERO_SPAN_TYPES = {"translation", "arabic_translation"}


def _is_word_slot(slot: dict[str, Any] | None) -> bool:
    return bool(slot and slot.get("kind") == "word")


def validate_graph(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    slots = graph.get("slots", [])
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    slot_index: dict[Any, dict[str, Any]] = {}
    object_ids: set[Any] = set()
    for slot in slots:
        slot_id = slot.get("id")
        if slot_id in object_ids:
            errors.append(f"duplicate graph id {slot_id!r}")
            continue
        object_ids.add(slot_id)
        slot_index[slot_id] = slot
        kind = slot.get("kind")
        if kind not in {"word", "synthetic"}:
            errors.append(f"slot {slot_id!r} has unsupported kind {kind!r}")
        elif kind == "word":
            if not slot.get("source_word_id"):
                errors.append(f"word slot {slot_id!r} lacks literal source_word_id")
        else:
            if slot.get("surface") not in {"", None}:
                errors.append(
                    f"synthetic slot {slot_id!r} must be surface-less; visible content is fabricated"
                )
            if slot.get("source_word_id") not in {None, ""}:
                errors.append(
                    f"synthetic slot {slot_id!r} must not masquerade as a source word"
                )

    node_index: dict[Any, dict[str, Any]] = {}
    for node in nodes:
        node_id = node.get("id")
        if node_id in object_ids:
            errors.append(f"duplicate graph id {node_id!r}")
            continue
        object_ids.add(node_id)
        node_index[node_id] = node
        for slot_id in node.get("slots", []):
            if slot_id not in slot_index:
                errors.append(
                    f"node {node_id!r} references unknown slot {slot_id!r}"
                )

    if graph.get("section_types") != ["document"]:
        errors.append(
            "universal section hierarchy must be document-only; sentence remains an ordinary node"
        )

    documents = [node for node in nodes if node.get("type") == "document"]
    source_record_ids: set[str] = set()
    section_addresses: set[tuple[Any, ...]] = set()
    slot_document_membership: Counter[Any] = Counter()
    for document in documents:
        features = document.get("features", {})
        source_record_id = features.get("source_record_id")
        if not source_record_id:
            errors.append(f"document {document.get('id')!r} lacks source_record_id")
        else:
            key = str(source_record_id).casefold()
            if key in source_record_ids:
                errors.append(
                    f"duplicate physical document source_record_id {source_record_id!r}"
                )
            source_record_ids.add(key)
        address = features.get("section_address")
        address_tuple = tuple(address) if isinstance(address, list) else ()
        if not address_tuple:
            errors.append(f"document {document.get('id')!r} lacks section address")
        elif address_tuple in section_addresses:
            errors.append(f"duplicate document section address {address_tuple!r}")
        else:
            section_addresses.add(address_tuple)
        for slot_id in document.get("slots", []):
            slot_document_membership[slot_id] += 1

    for slot_id in slot_index:
        membership = slot_document_membership[slot_id]
        if membership != 1:
            errors.append(
                f"slot {slot_id!r} must belong to exactly one physical document; found {membership}"
            )

    sentences = [node for node in nodes if node.get("type") == "sentence"]
    word_sentence_membership: Counter[Any] = Counter()
    for sentence in sentences:
        for slot_id in sentence.get("slots", []):
            slot = slot_index.get(slot_id)
            if slot and slot.get("kind") != "word":
                errors.append(
                    f"sentence {sentence.get('id')!r} must not absorb synthetic slot {slot_id!r}"
                )
            if slot and slot.get("kind") == "word":
                word_sentence_membership[slot_id] += 1
    for slot_id, slot in slot_index.items():
        if slot.get("kind") == "word" and word_sentence_membership[slot_id] != 1:
            errors.append(
                f"word slot {slot_id!r} must belong to exactly one sentence node; "
                f"found {word_sentence_membership[slot_id]}"
            )

    for node in nodes:
        node_type = node.get("type")
        features = node.get("features", {})
        node_slots = node.get("slots", [])

        if node_type in LAYOUT_TYPES and features.get("has_internal_boundary"):
            if not features.get("diplomatic_text") or features.get("render_mode") != "own_text":
                errors.append(
                    f"layout node {node.get('id')!r} with internal boundary requires own text rendering"
                )
            if "start_char" not in features or "end_char" not in features:
                errors.append(
                    f"layout node {node.get('id')!r} with internal boundary requires token-relative offsets"
                )

        if node_type in TEXTUAL_ZERO_SPAN_TYPES and features.get("zero_span"):
            valid = len(node_slots) == 1
            if valid:
                slot = slot_index.get(node_slots[0])
                valid = bool(
                    slot
                    and slot.get("kind") == "synthetic"
                    and slot.get("surface") in {"", None}
                )
            if not valid:
                errors.append(
                    f"zero-span textual node {node.get('id')!r} requires exactly one surface-less synthetic slot"
                )
            if features.get("render_mode") != "own_text" or not features.get("text"):
                errors.append(
                    f"zero-span textual node {node.get('id')!r} must render its literal own text"
                )

        if features.get("technical_anchor") and features.get("render_mode") not in {
            "none",
            "own_text",
        }:
            errors.append(
                f"technical anchor node {node.get('id')!r} must not render anchor slot text"
            )

    for edge in edges:
        edge_type = edge.get("type")
        source = edge.get("from")
        target = edge.get("to")
        if edge_type == "dependency_head":
            if not _is_word_slot(slot_index.get(source)) or not _is_word_slot(
                slot_index.get(target)
            ):
                errors.append(
                    f"dependency_head edge {source!r}->{target!r} must connect word slot to word slot"
                )
        elif edge_type == "entity_head":
            entity = node_index.get(source)
            if not entity or entity.get("type") != "entity":
                errors.append(f"entity_head edge source {source!r} is not an entity node")
                continue
            if not _is_word_slot(slot_index.get(target)):
                errors.append(
                    f"entity_head edge target {target!r} must be a word slot"
                )
            elif target not in entity.get("slots", []):
                errors.append(
                    f"entity_head edge target {target!r} is outside entity span {source!r}"
                )

    return errors
