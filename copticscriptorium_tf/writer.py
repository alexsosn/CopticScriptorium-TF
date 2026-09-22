"""Serialize a validated, writer-independent graph into a local Text-Fabric dataset.

No network access or source-data acquisition happens here. Write into an isolated
staging directory and publish only after every Text-Fabric feature batch saves.
"""
from __future__ import annotations

from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .graph import Graph, validate_graph


_META_SAFE_RE = re.compile(r"[a-z][a-z0-9_]*\Z")
_META_OCCURRENCE_SUFFIX_RE = re.compile(r"__\d+\Z")

# (feature name, slot attribute, node attribute, TF value type)
_SCALAR_FEATURES = (
    ("source_record_id", "source_record_id", "source_record_id", "str"),
    ("source_word_ordinal", "source_word_ordinal", None, "int"),
    ("source_id", "source_id", None, "str"),
    ("norm", "norm", None, "str"),
    ("lemma", "lemma", None, "str"),
    ("pos", "pos", None, "str"),
    ("func", "func", None, "str"),
    ("head_literal", "head_literal", "head_literal", "str"),
    ("dependency_head_ordinal", "dependency_head_ordinal", None, "int"),
    ("source_text", "source_text", None, "str"),
    ("source_ordinal", None, "source_ordinal", "int"),
    ("value", None, "value", "str"),
    ("own_text", None, "text", "str"),
    ("label", None, "label", "str"),
    ("scholarly_id", None, "scholarly_id", "str"),
    ("corpus", None, "corpus", "str"),
    ("dataset", None, "dataset", "str"),
    ("source_path", None, "source_path", "str"),
    ("source_sha256", None, "source_sha256", "str"),
    ("packaging", None, "packaging", "str"),
    ("entity_class", None, "entity_class", "str"),
    ("identity", None, "identity", "str"),
    ("render_mode", None, "render_mode", "str"),
    ("event_ordinal", None, "event_ordinal", "int"),
    ("start_word_ordinal", None, "start_word_ordinal", "int"),
    ("start_char", None, "start_char", "int"),
    ("start_after_word_ordinal", None, "start_after_word_ordinal", "int"),
    ("end_word_ordinal", None, "end_word_ordinal", "int"),
    ("end_char", None, "end_char", "int"),
    ("end_after_word_ordinal", None, "end_after_word_ordinal", "int"),
)

_EDGE_FEATURES = (
    "parent",
    "direct_word",
    "dependency_head",
    "entity_head",
    "same_scholarly",
    "same_scholarly_classification",
    "documented_overlap",
    "documented_overlap_classification",
    "documented_overlap_family",
    "witness",
    "witness_literal",
    "witness_target_scholarly_id",
)

_VALUED_EDGE_FEATURES = {
    "same_scholarly_classification",
    "documented_overlap_classification",
    "documented_overlap_family",
    "witness_literal",
    "witness_target_scholarly_id",
}


def _metadata_feature_name(key: str) -> str:
    """Return a deterministic, TF-safe and filesystem-safe feature name."""
    if not isinstance(key, str) or not key:
        raise ValueError("metadata keys must be non-empty strings")
    if _META_SAFE_RE.fullmatch(key) and not _META_OCCURRENCE_SUFFIX_RE.search(key):
        return f"meta_{key}"
    return f"meta__hex_{key.encode('utf-8').hex()}"


def _slot_ids(ranges):
    for first, last in ranges:
        yield from range(first, last + 1)


def _global_metadata(graph: Graph) -> dict[str, str]:
    return {
        "upstreamRepository": graph.upstream_repository,
        "upstreamCommit": graph.upstream_commit,
    }


def _batch_metadata(
    graph: Graph,
    *features: tuple[str, str, bool],
) -> dict[str, dict[str, str | bool]]:
    """Metadata for exactly the feature maps present in one save batch."""
    metadata: dict[str, dict[str, str | bool]] = {"": _global_metadata(graph)}
    for name, value_type, edge_values in features:
        feature_metadata: dict[str, str | bool] = {"valueType": value_type}
        if edge_values:
            feature_metadata["edgeValues"] = True
        metadata[name] = feature_metadata
    return metadata


def _put_scalar(
    data: dict[int, str | int],
    feature_name: str,
    node_id: int,
    value: str | int | None,
    value_type: str,
) -> None:
    if value is None:
        return
    expected = int if value_type == "int" else str
    if isinstance(value, bool) or not isinstance(value, expected):
        raise ValueError(
            f"unsupported value type for {feature_name}: {type(value).__name__}; "
            f"expected {value_type}"
        )
    data[node_id] = value


def _scalar_feature_data(
    graph: Graph,
    feature_name: str,
    slot_attribute: str | None,
    node_attribute: str | None,
    value_type: str,
) -> dict[int, str | int]:
    data: dict[int, str | int] = {}
    if slot_attribute is not None:
        for slot in graph.slots:
            _put_scalar(
                data,
                feature_name,
                slot.id,
                getattr(slot, slot_attribute),
                value_type,
            )
    if node_attribute is not None:
        for node in graph.nodes:
            _put_scalar(
                data,
                feature_name,
                node.id,
                getattr(node, node_attribute),
                value_type,
            )
    return data


def _diplomatic_feature_data(graph: Graph) -> dict[str, dict[int, str]]:
    """Project independently sourced diplomatic surfaces without extra slots."""
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

    return {
        "diplomatic_surface": surfaces,
        "diplomatic_after": separators,
    }


def _metadata_descriptors(graph: Graph) -> tuple[tuple[str, str, int], ...]:
    """Return collision-checked (feature, source key, occurrence) descriptors."""
    descriptors: dict[str, tuple[str, int]] = {}
    for node in graph.nodes:
        if node.otype != "document":
            continue
        metadata = dict(node.metadata)
        for key, value in node.metadata:
            if not isinstance(value, str):
                raise ValueError(f"metadata value for {key!r} must be a string")
            feature_name = _metadata_feature_name(key)
            descriptor = (key, 1)
            previous = descriptors.setdefault(feature_name, descriptor)
            if previous != descriptor:
                raise ValueError(f"metadata feature-name collision for {feature_name!r}")
        for key, values in node.metadata_duplicates:
            if key not in metadata:
                raise ValueError(f"duplicate metadata key {key!r} has no primary value")
            if not values or values[0] != metadata[key]:
                raise ValueError(
                    f"duplicate metadata evidence for {key!r} does not preserve the primary source value"
                )
            for occurrence, value in enumerate(values[1:], start=2):
                if not isinstance(value, str):
                    raise ValueError(f"metadata value for {key!r} must be a string")
                feature_name = f"{_metadata_feature_name(key)}__{occurrence}"
                descriptor = (key, occurrence)
                previous = descriptors.setdefault(feature_name, descriptor)
                if previous != descriptor:
                    raise ValueError(f"metadata feature-name collision for {feature_name!r}")
    return tuple(
        (feature_name, key, occurrence)
        for feature_name, (key, occurrence) in sorted(descriptors.items())
    )


def _metadata_feature_data(
    graph: Graph,
    key: str,
    occurrence: int,
) -> dict[int, str]:
    data: dict[int, str] = {}
    for node in graph.nodes:
        if node.otype != "document":
            continue
        if occurrence == 1:
            value = dict(node.metadata).get(key)
        else:
            values = dict(node.metadata_duplicates).get(key, ())
            value = values[occurrence - 1] if len(values) >= occurrence else None
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"metadata value for {key!r} must be a string")
            data[node.id] = value
    return data


def _add_unvalued_edge(
    data: dict[int, set[int]],
    feature_name: str,
    source: int,
    target: int,
) -> None:
    targets = data.setdefault(source, set())
    if target in targets:
        raise ValueError(f"duplicate {feature_name} edge for {source}->{target}")
    targets.add(target)


def _add_valued_edge(
    data: dict[int, dict[int, str]],
    feature_name: str,
    source: int,
    target: int,
    value: str | None,
) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise ValueError(f"valued edge {feature_name} requires a string value")
    targets = data.setdefault(source, {})
    if target in targets:
        raise ValueError(f"duplicate {feature_name} edge value for {source}->{target}")
    targets[target] = value


def _edge_feature_data(graph: Graph, feature_name: str) -> dict[int, object]:
    if feature_name == "parent":
        data: dict[int, set[int]] = {}
        for node in graph.nodes:
            if node.parent_node_id is not None:
                _add_unvalued_edge(data, feature_name, node.id, node.parent_node_id)
        return data

    if feature_name == "direct_word":
        data = {}
        for node in graph.nodes:
            for slot_id in node.direct_word_slots:
                _add_unvalued_edge(data, feature_name, node.id, slot_id)
        return data

    unvalued_kind = {
        "dependency_head": "dependency_head",
        "entity_head": "entity_head",
        "same_scholarly": "same_scholarly",
        "documented_overlap": "documented_overlap",
        "witness": "witness",
    }.get(feature_name)
    if unvalued_kind is not None:
        data = {}
        for edge in graph.edges:
            if edge.kind == unvalued_kind:
                _add_unvalued_edge(data, feature_name, edge.source, edge.target)
        return data

    valued_source = {
        "same_scholarly_classification": ("same_scholarly", "classification"),
        "documented_overlap_classification": ("documented_overlap", "classification"),
        "documented_overlap_family": ("documented_overlap", "family"),
        "witness_literal": ("witness", "witness_literal"),
        "witness_target_scholarly_id": ("witness", "target_scholarly_id"),
    }.get(feature_name)
    if valued_source is None:
        raise ValueError(f"unknown TF edge feature {feature_name!r}")
    kind, attribute = valued_source
    valued: dict[int, dict[int, str]] = {}
    for edge in graph.edges:
        if edge.kind == kind:
            _add_valued_edge(
                valued,
                feature_name,
                edge.source,
                edge.target,
                getattr(edge, attribute),
            )
    return valued


def _otext_metadata(graph: Graph) -> dict[str, str]:
    otext: dict[str, str] = {
        "sectionTypes": "document",
        "sectionFeatures": "source_record_id",
    }
    if any(slot.norm is not None for slot in graph.slots):
        otext["fmt:text-orig-full"] = "{norm} "

    has_diplomatic_surface = any(slot.source_text for slot in graph.slots) or any(
        node.otype in {"orig", "orig_group"} and node.value is not None
        for node in graph.nodes
    )
    if graph.slots and has_diplomatic_surface:
        otext["fmt:text-diplomatic-full"] = "{diplomatic_surface}{diplomatic_after}"

    if any(node.value is not None for node in graph.nodes):
        otext.update({
            "fmt:orig-default": "orig#{value}",
            "fmt:norm_group-default": "norm_group#{value}",
            "fmt:orig_group-default": "orig_group#{value}",
        })
    if any(node.text is not None for node in graph.nodes):
        otext.update({
            "fmt:translation-default": "translation#{own_text}",
            "fmt:arabic_translation-default": "arabic_translation#{own_text}",
            "fmt:page-default": "page#{own_text}",
            "fmt:column-default": "column#{own_text}",
            "fmt:line-default": "line#{own_text}",
        })
    return otext


def _projection_specs(graph: Graph):
    """Yield small descriptors; no descriptor retains projected feature data."""
    yield ("warp", None)
    for spec in _SCALAR_FEATURES:
        yield ("scalar", spec)
    yield ("diplomatic", None)
    for descriptor in _metadata_descriptors(graph):
        yield ("metadata", descriptor)
    for feature_name in _EDGE_FEATURES:
        yield ("edge", feature_name)
    yield ("otext", None)


def _project_batch(graph: Graph, spec):
    """Materialize at most one ordinary feature, or the two-feature warp/text batch."""
    kind, detail = spec

    if kind == "warp":
        otype = {slot.id: "word" for slot in graph.slots}
        oslots: dict[int, set[int]] = {}
        for node in graph.nodes:
            otype[node.id] = node.otype
            if not node.slot_ranges:
                raise ValueError(
                    f"{node.otype} node {node.id} has no measured word locus; reopen schema gate"
                )
            oslots[node.id] = set(_slot_ids(node.slot_ranges))
        return (
            {"otype": otype},
            {"oslots": oslots},
            _batch_metadata(
                graph,
                ("otype", "str", False),
                ("oslots", "str", False),
            ),
        )

    if kind == "scalar":
        feature_name, slot_attribute, node_attribute, value_type = detail
        data = _scalar_feature_data(
            graph,
            feature_name,
            slot_attribute,
            node_attribute,
            value_type,
        )
        if not data:
            return {}, {}, {"": _global_metadata(graph)}
        return (
            {feature_name: data},
            {},
            _batch_metadata(graph, (feature_name, value_type, False)),
        )

    if kind == "diplomatic":
        data = _diplomatic_feature_data(graph)
        return (
            data,
            {},
            _batch_metadata(
                graph,
                ("diplomatic_surface", "str", False),
                ("diplomatic_after", "str", False),
            ),
        )

    if kind == "metadata":
        feature_name, key, occurrence = detail
        data = _metadata_feature_data(graph, key, occurrence)
        if not data:
            return {}, {}, {"": _global_metadata(graph)}
        return (
            {feature_name: data},
            {},
            _batch_metadata(graph, (feature_name, "str", False)),
        )

    if kind == "edge":
        feature_name = detail
        data = _edge_feature_data(graph, feature_name)
        if not data:
            return {}, {}, {"": _global_metadata(graph)}
        return (
            {},
            {feature_name: data},
            _batch_metadata(
                graph,
                (feature_name, "str", feature_name in _VALUED_EDGE_FEATURES),
            ),
        )

    if kind == "otext":
        return (
            {},
            {},
            {
                "": _global_metadata(graph),
                "otext": _otext_metadata(graph),
            },
        )

    raise ValueError(f"unknown projection batch kind {kind!r}")


def _project(graph: Graph):
    """Compatibility/debug helper that aggregates the incremental projection.

    Production writing deliberately does not call this function because doing so
    retains every projected feature map simultaneously.
    """
    node_features: dict[str, dict[int, str | int]] = {}
    edge_features: dict[str, dict[int, object]] = {}
    metadata: dict[str, dict[str, str | bool]] = {}
    for spec in _projection_specs(graph):
        batch_nodes, batch_edges, batch_metadata = _project_batch(graph, spec)
        overlap = set(node_features).intersection(batch_nodes)
        if overlap:
            raise ValueError(f"duplicate projected node features: {sorted(overlap)}")
        overlap = set(edge_features).intersection(batch_edges)
        if overlap:
            raise ValueError(f"duplicate projected edge features: {sorted(overlap)}")
        node_features.update(batch_nodes)
        edge_features.update(batch_edges)
        for name, values in batch_metadata.items():
            if name == "":
                metadata.setdefault("", {}).update(values)
            elif name in metadata and metadata[name] != values:
                raise ValueError(f"conflicting projected metadata for {name}")
            else:
                metadata[name] = dict(values)
    return node_features, edge_features, metadata


def _remove_volatile_tf_write_metadata(directory: Path) -> None:
    """Remove Fabric's wall-clock header while preserving feature data byte-for-byte."""
    for path in directory.glob("*.tf"):
        lines = path.read_bytes().splitlines(keepends=True)
        normalized: list[bytes] = []
        in_header = True
        for line in lines:
            if in_header and line.rstrip(b"\r\n") == b"":
                in_header = False
            if in_header and line.startswith(b"@dateWritten="):
                continue
            normalized.append(line)
        path.write_bytes(b"".join(normalized))


def write_graph(graph: Graph, destination: Path | str) -> Path:
    """Write atomically to a fresh destination; fail closed on invalid graph/TF."""
    errors = validate_graph(graph)
    if errors:
        raise ValueError("graph validation failed: " + "; ".join(errors[:8]))
    target = Path(destination)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing TF dataset: {target}")
    from tf.fabric import Fabric

    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".tf-staging-", dir=target.parent) as temporary:
        staging = Path(temporary)
        fabric = Fabric(locations=[str(staging)], silent="deep")
        specs = iter(_projection_specs(graph))
        while True:
            try:
                spec = next(specs)
            except StopIteration:
                break
            node_features, edge_features, metadata = _project_batch(graph, spec)
            if not node_features and not edge_features and set(metadata) == {""}:
                del node_features, edge_features, metadata
                continue
            success = fabric.save(
                nodeFeatures=node_features,
                edgeFeatures=edge_features,
                metaData=metadata,
                silent="deep",
            )
            batch_label = ",".join(
                sorted((*node_features.keys(), *edge_features.keys(), *(k for k in metadata if k)))
            )
            del node_features, edge_features, metadata
            if not success:
                raise ValueError(
                    f"Text-Fabric save failed for batch {batch_label}; no dataset published"
                )
        required = ("otype.tf", "oslots.tf", "otext.tf")
        if any(not (staging / name).is_file() for name in required):
            raise ValueError("Text-Fabric omitted mandatory warp/otext files")
        _remove_volatile_tf_write_metadata(staging)
        staging.rename(target)
    return target
