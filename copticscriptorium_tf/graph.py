"""Public graph API and issue-2 document-relation derivation."""
from __future__ import annotations

from itertools import combinations
import re
from typing import Sequence

from ._graph_core import (
    DOCUMENT_RELATION_TYPES,
    LAYOUT_TYPES,
    NODE_TYPE_ORDER,
    OVERLAP_CLASSES,
    DocumentRelation,
    Graph,
    GraphEdge,
    GraphNode,
    GraphSlot,
    NodeRange,
    build_graph as _build_graph,
    graph_fingerprint,
    validate_graph,
)
from .model import DocumentModel

WITNESS_CTS_RE = re.compile(r"urn:cts:[^\s]+")
DOCUMENTED_COLLECTION_OVERLAP_SPECS = (
    (
        "sahidica.mark/sahidica.mark", "Mark_",
        "sahidica.nt/sahidica.nt", "41_Mark_",
        range(1, 17),
    ),
    (
        "sahidica.1corinthians/sahidica.1corinthians", "1Cor_",
        "sahidica.nt/sahidica.nt", "46_1_Corinthians_",
        range(1, 17),
    ),
    (
        "sahidic.ruth/sahidic.ruth", "Ruth_",
        "sahidic.ot/sahidic.ot", "08_Ruth_",
        range(1, 5),
    ),
)


def _ordered_documents(documents: Sequence[DocumentModel]) -> tuple[DocumentModel, ...]:
    ordered = tuple(sorted(
        documents,
        key=lambda document: (document.source_record_id.casefold(), document.source_record_id),
    ))
    seen: set[str] = set()
    for document in ordered:
        technical = document.source_record_id.casefold()
        if technical in seen:
            raise ValueError(
                f"duplicate physical document source_record_id {document.source_record_id!r}"
            )
        seen.add(technical)
    repositories = {document.upstream_repository for document in ordered}
    commits = {document.upstream_commit for document in ordered}
    if len(repositories) > 1 or len(commits) > 1:
        raise ValueError("document relations require one exact upstream repository revision")
    return ordered


def _classify_documents(left: DocumentModel, right: DocumentModel) -> str:
    if left.source_sha256 == right.source_sha256:
        return "byte_identical"
    if (
        tuple(word.norm for word in left.words) != tuple(word.norm for word in right.words)
        or tuple(item.value for item in left.origs) != tuple(item.value for item in right.origs)
    ):
        return "textual_divergence"
    left_analysis = tuple(
        (word.norm, word.lemma, word.pos, word.func, word.dependency_head_ordinal)
        for word in left.words
    )
    right_analysis = tuple(
        (word.norm, word.lemma, word.pos, word.func, word.dependency_head_ordinal)
        for word in right.words
    )
    if left_analysis != right_analysis:
        return "alternate_analysis"
    return "core_identical_source_variant"


def _extract_witness_cts_targets(value: str) -> tuple[str, ...]:
    targets: list[str] = []
    for match in WITNESS_CTS_RE.finditer(value):
        target = match.group(0).rstrip(".,;!?)]}")
        if target not in targets:
            targets.append(target)
    return tuple(targets)


def _relation_sort_key(item: DocumentRelation) -> tuple[str, ...]:
    return (
        item.kind,
        item.source_record_id.casefold(),
        item.source_record_id,
        item.target_record_id.casefold(),
        item.target_record_id,
        item.classification or "",
        item.family or "",
        item.witness_literal or "",
        item.target_scholarly_id or "",
    )


def derive_document_relations(
    documents: Sequence[DocumentModel],
) -> tuple[DocumentRelation, ...]:
    """Derive reviewed issue-2 relations without collapsing physical records."""
    ordered = _ordered_documents(documents)
    by_record = {document.source_record_id: document for document in ordered}
    by_scholarly: dict[str, list[DocumentModel]] = {}
    for document in ordered:
        if document.scholarly_id:
            by_scholarly.setdefault(document.scholarly_id, []).append(document)

    relations: list[DocumentRelation] = []
    for scholarly_id in sorted(by_scholarly):
        for left, right in combinations(by_scholarly[scholarly_id], 2):
            relations.append(DocumentRelation(
                "same_scholarly",
                left.source_record_id,
                right.source_record_id,
                classification=_classify_documents(left, right),
            ))

    for (
        left_dataset,
        left_prefix,
        right_dataset,
        right_prefix,
        chapters,
    ) in DOCUMENTED_COLLECTION_OVERLAP_SPECS:
        for chapter in chapters:
            chapter_text = f"{chapter:02d}"
            left = by_record.get(f"{left_dataset}:{left_prefix}{chapter_text}")
            right = by_record.get(f"{right_dataset}:{right_prefix}{chapter_text}")
            if left is None or right is None:
                continue
            relations.append(DocumentRelation(
                "documented_overlap",
                left.source_record_id,
                right.source_record_id,
                classification=_classify_documents(left, right),
                family="book_aggregate",
            ))

    for source in ordered:
        witness = source.metadata.get("witness")
        if not witness:
            continue
        for target_scholarly_id in _extract_witness_cts_targets(witness):
            targets = by_scholarly.get(target_scholarly_id)
            if not targets:
                raise ValueError(
                    f"unresolved witness CTS target {target_scholarly_id!r} "
                    f"in {source.source_record_id}"
                )
            # The source relation names a scholarly identity. With no separate
            # scholarly-identity node in the reviewed schema, project it onto
            # every physical document carrying that identity rather than
            # choosing an arbitrary preferred copy.
            for target in targets:
                relations.append(DocumentRelation(
                    "witness",
                    source.source_record_id,
                    target.source_record_id,
                    witness_literal=witness,
                    target_scholarly_id=target_scholarly_id,
                ))

    relations.sort(key=_relation_sort_key)
    return tuple(relations)


def build_graph(
    documents: Sequence[DocumentModel],
    *,
    document_relations: Sequence[DocumentRelation] | None = None,
) -> Graph:
    """Build the deterministic graph, deriving issue-2 relations by default."""
    materialized = tuple(documents)
    if document_relations is None:
        document_relations = derive_document_relations(materialized)
    return _build_graph(materialized, document_relations=document_relations)


__all__ = [
    "DOCUMENT_RELATION_TYPES",
    "LAYOUT_TYPES",
    "NODE_TYPE_ORDER",
    "OVERLAP_CLASSES",
    "DocumentRelation",
    "Graph",
    "GraphEdge",
    "GraphNode",
    "GraphSlot",
    "NodeRange",
    "build_graph",
    "derive_document_relations",
    "graph_fingerprint",
    "validate_graph",
]
