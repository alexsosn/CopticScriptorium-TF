"""Serialize a validated, writer-independent graph into a local Text-Fabric dataset.

No network access or source-data acquisition happens here. Write into an isolated
staging directory and publish only after Fabric.save() reports success.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .graph import Graph, validate_graph


_META_SAFE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
_META_OCCURRENCE_SUFFIX_RE = re.compile(r"__\d+\Z")


def _metadata_feature_name(key: str) -> str:
    """Return a deterministic, TF-safe and injective feature name for a metadata key.

    Ordinary Coptic Scriptorium keys remain readable. Keys unsafe for TF feature
    names, and keys that could collide with the ``__N`` duplicate-occurrence
    namespace, are represented by reversible UTF-8 hex.
    """
    if not isinstance(key, str) or not key:
        raise ValueError("metadata keys must be non-empty strings")
    if _META_SAFE_RE.fullmatch(key) and not _META_OCCURRENCE_SUFFIX_RE.search(key):
        return f"meta_{key}"
    return f"meta__hex_{key.encode('utf-8').hex()}"


def _slot_ids(ranges):
    for first, last in ranges:
        yield from range(first, last + 1)


def _diplomatic_features(graph: Graph, node_features: dict[str, dict[int, str | int]]) -> None:
    """Project independently sourced diplomatic surfaces without extra slots.

    Source original units override per-word fallback. Nested original-group
    literals have final authority over child originals; direct words under a
    norm-group retain their own source text. Only group-final words receive a
    separator; group-internal words concatenate. Layout nodes separately own
    their character-accurate, potentially word-internal source text.
    """
    surfaces = {slot.id: slot.source_text for slot in graph.slots if slot.source_text}
    separators = {slot.id: " " for slot in graph.slots}

    def terminate_group(node) -> tuple[int, ...]:
        ids = tuple(_slot_ids(node.slot_ranges))
        if not ids:
            raise ValueError(f"{node.otype} {node.id} has no diplomatic locus")
        for slot_id in ids[:-1]:
            separators.pop(slot_id, None)
        separators[ids[-1]] = " "
        return ids

    for node in graph.nodes:
        if node.otype != "orig":
            continue
        ids = tuple(_slot_ids(node.slot_ranges))
        if node.value is not None and ids:
            surfaces[ids[0]] = node.value
            for slot_id in ids[1:]:
                surfaces.pop(slot_id, None)

    for node in graph.nodes:
        if node.otype == "norm_group":
            terminate_group(node)

    for node in graph.nodes:
        if node.otype != "orig_group":
            continue
        ids = terminate_group(node)
        if node.value is not None:
            surfaces[ids[0]] = node.value
            for slot_id in ids[1:]:
                surfaces.pop(slot_id, None)

    node_features["diplomatic_surface"] = surfaces
    node_features["diplomatic_after"] = separators


def _project(graph: Graph):
    """Produce TF typed scalar features and directed edge maps without renumbering."""
    node_features: dict[str, dict[int, str | int]] = defaultdict(dict)
    edge_features: dict[str, dict[int, object]] = defaultdict(dict)
    value_types: dict[str, str] = {}
    valued_edge_features: set[str] = set()

    node_features["otype"] = {slot.id: "word" for slot in graph.slots}
    for node in graph.nodes:
        node_features["otype"][node.id] = node.otype
        if not node.slot_ranges:
            raise ValueError(f"{node.otype} node {node.id} has no measured word locus; reopen schema gate")
        edge_features["oslots"][node.id] = set(_slot_ids(node.slot_ranges))

    def put(name: str, node_id: int, value: str | int | None) -> None:
        if value is None:
            return
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            raise ValueError(f"unsupported value type for {name}: {type(value).__name__}")
        kind = "int" if isinstance(value, int) else "str"
        previous = value_types.setdefault(name, kind)
        if previous != kind:
            raise ValueError(f"mixed TF value types for {name}")
        node_features[name][node_id] = value

    def add_unvalued_edge(name: str, source: int, target: int) -> None:
        targets = edge_features[name].setdefault(source, set())
        if not isinstance(targets, set):
            raise ValueError(f"edge feature {name} mixes valued and unvalued edges")
        if target in targets:
            raise ValueError(f"duplicate {name} edge for {source}->{target}")
        targets.add(target)

    def add_valued_edge(name: str, source: int, target: int, value: str | None) -> None:
        if value is None:
            return
        if not isinstance(value, str):
            raise ValueError(f"valued edge {name} requires a string value")
        targets = edge_features[name].setdefault(source, {})
        if not isinstance(targets, dict):
            raise ValueError(f"edge feature {name} mixes valued and unvalued edges")
        if target in targets:
            raise ValueError(f"duplicate {name} edge value for {source}->{target}")
        targets[target] = value
        valued_edge_features.add(name)

    for slot in graph.slots:
        for name in (
            "source_record_id", "source_word_ordinal", "source_id", "norm", "lemma",
            "pos", "func", "head_literal", "dependency_head_ordinal", "source_text",
        ):
            put(name, slot.id, getattr(slot, name))

    _diplomatic_features(graph, node_features)
    value_types["diplomatic_surface"] = "str"
    value_types["diplomatic_after"] = "str"

    for node in graph.nodes:
        for name in (
            "source_record_id", "source_ordinal", "value", "text", "label",
            "scholarly_id", "corpus", "dataset", "source_path", "source_sha256",
            "packaging", "entity_class", "identity", "head_literal",
            "render_mode", "event_ordinal", "start_word_ordinal", "start_char",
            "start_after_word_ordinal", "end_word_ordinal", "end_char",
            "end_after_word_ordinal",
        ):
            feature_name = "own_text" if name == "text" else name
            put(feature_name, node.id, getattr(node, name))

        if node.parent_node_id is not None:
            add_unvalued_edge("parent", node.id, node.parent_node_id)

        if node.otype == "document":
            metadata = dict(node.metadata)
            for key, value in node.metadata:
                put(_metadata_feature_name(key), node.id, value)
            for key, values in node.metadata_duplicates:
                if key not in metadata:
                    raise ValueError(f"duplicate metadata key {key!r} has no primary value")
                if not values or values[0] != metadata[key]:
                    raise ValueError(
                        f"duplicate metadata evidence for {key!r} does not preserve the primary source value"
                    )
                for occurrence, value in enumerate(values[1:], start=2):
                    put(f"{_metadata_feature_name(key)}__{occurrence}", node.id, value)

        if node.direct_word_slots:
            for slot_id in node.direct_word_slots:
                add_unvalued_edge("direct_word", node.id, slot_id)

    for edge in graph.edges:
        if edge.kind in {"dependency_head", "entity_head"}:
            add_unvalued_edge(edge.kind, edge.source, edge.target)
        elif edge.kind == "same_scholarly":
            add_unvalued_edge("same_scholarly", edge.source, edge.target)
            add_valued_edge(
                "same_scholarly_classification",
                edge.source,
                edge.target,
                edge.classification,
            )
        elif edge.kind == "documented_overlap":
            add_unvalued_edge("documented_overlap", edge.source, edge.target)
            add_valued_edge(
                "documented_overlap_classification",
                edge.source,
                edge.target,
                edge.classification,
            )
            add_valued_edge(
                "documented_overlap_family",
                edge.source,
                edge.target,
                edge.family,
            )
        elif edge.kind == "witness":
            add_unvalued_edge("witness", edge.source, edge.target)
            add_valued_edge(
                "witness_literal",
                edge.source,
                edge.target,
                edge.witness_literal,
            )
            add_valued_edge(
                "witness_target_scholarly_id",
                edge.source,
                edge.target,
                edge.target_scholarly_id,
            )
        else:
            raise ValueError(f"unknown graph edge kind {edge.kind!r}")

    metadata: dict[str, dict[str, str | bool]] = {
        name: {"valueType": value_type}
        for name, value_type in value_types.items()
    }
    metadata["otype"] = {"valueType": "str"}
    for name in edge_features:
        metadata[name] = {"valueType": "str"}
        if name in valued_edge_features:
            metadata[name]["edgeValues"] = True

    otext: dict[str, str] = {
        "sectionTypes": "document",
        "sectionFeatures": "source_record_id",
    }
    if node_features.get("norm"):
        otext["fmt:text-orig-full"] = "{norm} "
    if node_features.get("diplomatic_surface") and node_features.get("diplomatic_after"):
        otext["fmt:text-diplomatic-full"] = "{diplomatic_surface}{diplomatic_after}"
    if node_features.get("value"):
        otext.update({
            "fmt:orig-default": "orig#{value}",
            "fmt:norm_group-default": "norm_group#{value}",
            "fmt:orig_group-default": "orig_group#{value}",
        })
    if node_features.get("own_text"):
        otext.update({
            "fmt:translation-default": "translation#{own_text}",
            "fmt:arabic_translation-default": "arabic_translation#{own_text}",
            "fmt:page-default": "page#{own_text}",
            "fmt:column-default": "column#{own_text}",
            "fmt:line-default": "line#{own_text}",
        })
    metadata["otext"] = otext
    metadata[""] = {
        "upstreamRepository": graph.upstream_repository,
        "upstreamCommit": graph.upstream_commit,
    }
    return dict(node_features), dict(edge_features), metadata


def write_graph(graph: Graph, destination: Path | str) -> Path:
    """Write atomically to a fresh destination; fail closed on invalid graph/TF."""
    errors = validate_graph(graph)
    if errors:
        raise ValueError("graph validation failed: " + "; ".join(errors[:8]))
    target = Path(destination)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing TF dataset: {target}")
    node_features, edge_features, metadata = _project(graph)
    from tf.fabric import Fabric

    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".tf-staging-", dir=target.parent) as temporary:
        staging = Path(temporary)
        fabric = Fabric(locations=[str(staging)], silent="deep")
        success = fabric.save(
            nodeFeatures=node_features,
            edgeFeatures=edge_features,
            metaData=metadata,
            silent="deep",
        )
        if not success:
            raise ValueError("Text-Fabric save failed; no dataset published")
        required = ("otype.tf", "oslots.tf", "otext.tf")
        if any(not (staging / name).is_file() for name in required):
            raise ValueError("Text-Fabric omitted mandatory warp/otext files")
        staging.rename(target)
    return target
