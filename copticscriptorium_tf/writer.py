"""Serialize a validated, writer-independent graph into a local Text-Fabric dataset.

No network access or source-data acquisition happens here. Write into an isolated
staging directory and publish only after Fabric.save() reports success.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .graph import Graph, validate_graph


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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
    """Produce TF's typed scalar features and directed edge maps without renumbering."""
    node_features: dict[str, dict[int, str | int]] = defaultdict(dict)
    edge_features: dict[str, dict[int, object]] = defaultdict(dict)
    value_types: dict[str, str] = {}
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
            "packaging", "parent_node_id", "entity_class", "identity", "head_literal",
            "render_mode", "event_ordinal", "start_word_ordinal", "start_char",
            "start_after_word_ordinal", "end_word_ordinal", "end_char",
            "end_after_word_ordinal",
        ):
            feature_name = "own_text" if name == "text" else name
            put(feature_name, node.id, getattr(node, name))
        if node.otype == "document":
            put("metadata_json", node.id, _json(dict(node.metadata)))
            put("metadata_duplicates_json", node.id, _json(dict(node.metadata_duplicates)))
        if node.direct_word_slots:
            put("direct_word_slots_json", node.id, _json(node.direct_word_slots))
        if node.section_address:
            put("section_address_json", node.id, _json(node.section_address))

    # The relation evidence is a deterministic string on the directed edge.
    # A TF valued edge's .f(source) maps targets to values; target identity is
    # never chosen by a lossy source-record deduplication operation.
    for edge in graph.edges:
        if edge.kind in {"dependency_head", "entity_head"}:
            targets = edge_features[edge.kind].setdefault(edge.source, set())
            targets.add(edge.target)
        else:
            targets = edge_features[edge.kind].setdefault(edge.source, {})
            if edge.kind == "same_scholarly":
                evidence = edge.classification or ""
            elif edge.kind == "documented_overlap":
                evidence = _json({"classification": edge.classification, "family": edge.family})
            elif edge.kind == "witness":
                evidence = _json({
                    "witness_literal": edge.witness_literal,
                    "target_scholarly_id": edge.target_scholarly_id,
                })
            else:
                raise ValueError(f"unknown graph edge kind {edge.kind!r}")
            if edge.target in targets:
                raise ValueError(f"multiple {edge.kind} edges for {edge.source}->{edge.target} cannot be represented losslessly")
            targets[edge.target] = evidence

    metadata: dict[str, dict[str, str | bool]] = {
        name: {"valueType": value_type}
        for name, value_type in value_types.items()
    }
    metadata["otype"] = {"valueType": "str"}
    for name in edge_features:
        metadata[name] = {"valueType": "str"}
        if name in {"same_scholarly", "documented_overlap", "witness"}:
            metadata[name]["edgeValues"] = True
    metadata["otext"] = {
        "sectionTypes": "document",
        "sectionFeatures": "source_record_id",
        "fmt:text-orig-full": "{norm} ",
        "fmt:text-diplomatic-full": "{diplomatic_surface}{diplomatic_after}",
        "fmt:orig-default": "orig#{value}",
        "fmt:norm_group-default": "norm_group#{value}",
        "fmt:orig_group-default": "orig_group#{value}",
        "fmt:translation-default": "translation#{own_text}",
        "fmt:arabic_translation-default": "arabic_translation#{own_text}",
        "fmt:page-default": "page#{own_text}",
        "fmt:column-default": "column#{own_text}",
        "fmt:line-default": "line#{own_text}",
    }
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
