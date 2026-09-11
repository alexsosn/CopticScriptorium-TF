"""Synthetic graph-contract validator for CopticScriptorium-TF issue #3.

This module validates research fixtures for the proposed intermediate graph. It is
not a Text-Fabric writer. The contract exists so later implementation tickets have
machine-testable invariants derived from the corpus-wide research evidence.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


LAYOUT_TYPES = {"page", "column", "line"}
TEXTUAL_TYPES = {"translation", "arabic_translation"}
TEXTUAL_ZERO_SPAN_TYPES = TEXTUAL_TYPES
OVERLAP_CLASSES = {
    "byte_identical",
    "core_identical_source_variant",
    "alternate_analysis",
    "textual_divergence",
}


def _is_word_slot(slot: dict[str, Any] | None) -> bool:
    return bool(slot and slot.get("kind") == "word")


def _is_document(node: dict[str, Any] | None) -> bool:
    return bool(node and node.get("type") == "document")


def validate_graph(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    slots = graph.get("slots", [])
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    provenance = graph.get("provenance", {})
    if not provenance.get("upstream_repository") or not provenance.get("upstream_commit"):
        errors.append(
            "graph provenance requires upstream_repository and upstream_commit"
        )

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
    slot_document_owners: dict[Any, set[Any]] = defaultdict(set)
    for document in documents:
        document_id = document.get("id")
        features = document.get("features", {})
        source_record_id = features.get("source_record_id")
        if not source_record_id:
            errors.append(f"document {document_id!r} lacks source_record_id")
        else:
            key = str(source_record_id).casefold()
            if key in source_record_ids:
                errors.append(
                    f"duplicate physical document source_record_id {source_record_id!r}"
                )
            source_record_ids.add(key)
        if not features.get("corpus"):
            errors.append(f"document {document_id!r} lacks corpus feature")
        if not features.get("dataset"):
            errors.append(f"document {document_id!r} lacks dataset feature")
        if not features.get("source_path"):
            errors.append(f"document {document_id!r} lacks source_path provenance")
        if not features.get("source_sha256"):
            errors.append(f"document {document_id!r} lacks source_sha256 provenance")
        address = features.get("section_address")
        address_tuple = tuple(address) if isinstance(address, list) else ()
        if not address_tuple:
            errors.append(f"document {document_id!r} lacks section address")
        else:
            if source_record_id and address != [source_record_id]:
                errors.append(
                    f"document {document_id!r} section address must be [source_record_id]"
                )
            if address_tuple in section_addresses:
                errors.append(f"duplicate document section address {address_tuple!r}")
            else:
                section_addresses.add(address_tuple)
        for slot_id in document.get("slots", []):
            slot_document_membership[slot_id] += 1
            slot_document_owners[slot_id].add(document_id)

    for slot_id in slot_index:
        membership = slot_document_membership[slot_id]
        if membership != 1:
            errors.append(
                f"slot {slot_id!r} must belong to exactly one physical document; found {membership}"
            )

    for node in nodes:
        if node.get("type") == "document":
            continue
        node_slots = node.get("slots", [])
        owners: set[Any] = set()
        for slot_id in node_slots:
            owners.update(slot_document_owners.get(slot_id, set()))
        if len(owners) > 1:
            errors.append(
                f"{node.get('type')} node {node.get('id')!r} crosses physical documents"
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

        if node_type in LAYOUT_TYPES:
            if "diplomatic_text" not in features or features.get("render_mode") != "own_text":
                errors.append(
                    f"layout node {node.get('id')!r} requires own text rendering"
                )
            if features.get("has_internal_boundary") and (
                "start_char" not in features or "end_char" not in features
            ):
                errors.append(
                    f"layout node {node.get('id')!r} with internal boundary requires token-relative offsets"
                )

        if node_type in TEXTUAL_TYPES:
            if "text" not in features or features.get("render_mode") != "own_text":
                errors.append(
                    f"{node_type} node {node.get('id')!r} must render its own text"
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
            if not features.get("text"):
                errors.append(
                    f"zero-span textual node {node.get('id')!r} must retain non-empty literal text"
                )
            if (
                "after_source_word_ordinal" not in features
                or "source_char_offset" not in features
            ):
                errors.append(
                    f"zero-span textual node {node.get('id')!r} requires deterministic source order locus"
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
        features = edge.get("features", {})
        if edge_type == "dependency_head":
            source_slot = slot_index.get(source)
            target_slot = slot_index.get(target)
            if not _is_word_slot(source_slot) or not _is_word_slot(target_slot):
                errors.append(
                    f"dependency_head edge {source!r}->{target!r} must connect word slot to word slot"
                )
            else:
                source_owners = slot_document_owners.get(source, set())
                target_owners = slot_document_owners.get(target, set())
                if (
                    len(source_owners) == 1
                    and len(target_owners) == 1
                    and source_owners != target_owners
                ):
                    errors.append(
                        f"dependency_head edge {source!r}->{target!r} crosses physical documents"
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
            else:
                entity_owners: set[Any] = set()
                for slot_id in entity.get("slots", []):
                    entity_owners.update(slot_document_owners.get(slot_id, set()))
                target_owners = slot_document_owners.get(target, set())
                if (
                    len(entity_owners) == 1
                    and len(target_owners) == 1
                    and entity_owners != target_owners
                ):
                    errors.append(
                        f"entity_head edge {source!r}->{target!r} crosses physical documents"
                    )
        elif edge_type in {"same_scholarly", "documented_overlap", "witness"}:
            source_document = node_index.get(source)
            target_document = node_index.get(target)
            if not _is_document(source_document) or not _is_document(target_document):
                errors.append(
                    f"{edge_type} edge {source!r}->{target!r} must connect document nodes"
                )
                continue
            if edge_type in {"same_scholarly", "documented_overlap"}:
                classification = features.get("classification")
                if classification not in OVERLAP_CLASSES:
                    errors.append(
                        f"{edge_type} edge {source!r}->{target!r} requires a measured classification"
                    )
                if edge_type == "same_scholarly":
                    source_scholarly = source_document.get("features", {}).get("scholarly_id")
                    target_scholarly = target_document.get("features", {}).get("scholarly_id")
                    if not source_scholarly or source_scholarly != target_scholarly:
                        errors.append(
                            f"same_scholarly edge {source!r}->{target!r} requires matching scholarly_id"
                        )
                elif not features.get("family"):
                    errors.append(
                        f"documented_overlap edge {source!r}->{target!r} requires relation family"
                    )
            else:
                witness_literal = features.get("witness_literal")
                target_scholarly_id = features.get("target_scholarly_id")
                if not witness_literal:
                    errors.append(
                        f"witness edge {source!r}->{target!r} requires literal witness evidence"
                    )
                if not target_scholarly_id:
                    errors.append(
                        f"witness edge {source!r}->{target!r} requires target scholarly identity"
                    )
                elif target_document.get("features", {}).get("scholarly_id") != target_scholarly_id:
                    errors.append(
                        f"witness edge {source!r}->{target!r} target document scholarly_id does not match target_scholarly_id"
                    )

    return errors
