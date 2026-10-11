"""Executable CopticScriptorium-TF research recipes.

Run directly:

    python examples/query_cookbook.py /path/to/generated-tf --lemma lemma-value

or import the functions into a notebook/script. All recipes read native TF
features/edges; they do not depend on converter internals or semantic sidecars.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tf.fabric import Fabric


NODE_FEATURES = {
    "source_record_id",
    "source_word_ordinal",
    "source_id",
    "norm",
    "lemma",
    "pos",
    "func",
    "source_text",
    "scholarly_id",
    "corpus",
    "dataset",
    "source_path",
    "source_sha256",
    "packaging",
    "entity_class",
    "identity",
    "own_text",
    "start_word_ordinal",
    "start_char",
    "start_after_word_ordinal",
    "end_word_ordinal",
    "end_char",
    "end_after_word_ordinal",
    "conllu_status",
    "conllu_source_path",
    "conllu_source_sha256",
}
EDGE_FEATURES = {
    "parent",
    "direct_word",
    "dependency_head",
    "ud_head",
    "entity_head",
    "same_scholarly",
    "same_scholarly_classification",
    "documented_overlap",
    "documented_overlap_classification",
    "documented_overlap_family",
    "witness",
    "witness_literal",
    "witness_target_scholarly_id",
}
DOCUMENT_RELATIONS = {"same_scholarly", "documented_overlap", "witness"}


def load_generated_tf(location: Path | str):
    """Load cookbook features from one generated native TF directory."""
    tf = Fabric(locations=[str(location)], silent="deep")
    inventory = tf.explore(silent="deep", show=True)
    available_nodes = set(inventory["nodes"])
    available_edges = set(inventory["edges"])
    wanted_nodes = sorted(
        feature
        for feature in available_nodes
        if feature in NODE_FEATURES or feature.startswith(("meta_", "ud_"))
    )
    wanted_edges = sorted(
        feature for feature in available_edges if feature in EDGE_FEATURES
    )
    features = wanted_nodes + wanted_edges
    api = tf.load(" ".join(features), silent="deep")
    if not api:
        raise RuntimeError(f"Text-Fabric failed to load generated corpus at {location}")
    return api


def _node_features(api) -> set[str]:
    return set(api.Fall())


def _edge_features(api) -> set[str]:
    return set(api.Eall())


def _require_node_feature(api, feature: str) -> None:
    if feature not in _node_features(api):
        raise ValueError(f"generated corpus does not contain node feature {feature!r}")


def _require_edge_feature(api, feature: str) -> None:
    if feature not in _edge_features(api):
        raise ValueError(f"generated corpus does not contain edge feature {feature!r}")


def _search_literal(value: str) -> str:
    """Escape the TF-search separators used by cookbook literal values."""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace(" ", "\\ ")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
    )


def lemma_hits(api, lemma: str) -> tuple[tuple[int, ...], ...]:
    """Return one-node tuples for words whose lemma equals lemma."""
    _require_node_feature(api, "lemma")
    return tuple(api.S.search(f"word lemma={_search_literal(lemma)}", silent="deep"))


def morphology_hits(
    api,
    *,
    pos: str | None = None,
    func: str | None = None,
) -> tuple[tuple[int, ...], ...]:
    """Filter word slots by the source POS/function annotations."""
    if pos is None and func is None:
        raise ValueError("provide pos and/or func")
    specs = ["word"]
    if pos is not None:
        _require_node_feature(api, "pos")
        specs.append(f"pos={_search_literal(pos)}")
    if func is not None:
        _require_node_feature(api, "func")
        specs.append(f"func={_search_literal(func)}")
    return tuple(api.S.search(" ".join(specs), silent="deep"))


def dependency_pairs(
    api,
    *,
    func: str | None = None,
) -> tuple[tuple[int, int], ...]:
    """Return (dependent, head) word pairs; roots have no dependency edge."""
    _require_edge_feature(api, "dependency_head")
    dep_spec = "dependent:word"
    if func is not None:
        _require_node_feature(api, "func")
        dep_spec += f" func={_search_literal(func)}"
    query = f"""\
{dep_spec}
head:word
dependent -dependency_head> head
"""
    return tuple(api.S.search(query, silent="deep"))


def ud_hits(api, **constraints: str) -> tuple[tuple[int, ...], ...]:
    """Filter word slots by supplemental UD features, e.g. ud_upos="VERB".

    Keys are generated feature names such as ud_feat_verb_form; only words of
    CoNLL-U-supplemented records carry these values.
    """
    if not constraints:
        raise ValueError("provide at least one ud_* feature constraint")
    specs = ["word"]
    for feature, value in sorted(constraints.items()):
        if not feature.startswith("ud_"):
            raise ValueError(f"{feature!r} is not a supplemental UD feature")
        _require_node_feature(api, feature)
        specs.append(f"{feature}={_search_literal(value)}")
    return tuple(api.S.search(" ".join(specs), silent="deep"))


def ud_dependency_pairs(
    api,
    *,
    deprel: str | None = None,
) -> tuple[tuple[int, int], ...]:
    """Return (dependent, head) pairs from CoNLL-U heads, including TT-absent ones."""
    _require_edge_feature(api, "ud_head")
    dep_spec = "dependent:word"
    if deprel is not None:
        _require_node_feature(api, "ud_deprel")
        dep_spec += f" ud_deprel={_search_literal(deprel)}"
    query = f"""\
{dep_spec}
head:word
dependent -ud_head> head
"""
    return tuple(api.S.search(query, silent="deep"))


def entity_head_occurrences(
    api,
    *,
    entity_class: str | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return entity nodes with their measured word span and head word."""
    _require_edge_feature(api, "entity_head")
    entity_spec = "entity:entity"
    if entity_class is not None:
        _require_node_feature(api, "entity_class")
        entity_spec += f" entity_class={_search_literal(entity_class)}"
    query = f"""\
{entity_spec}
head:word
entity -entity_head> head
"""
    rows = api.S.search(query, silent="deep")
    return tuple(
        {
            "entity": entity,
            "head": head,
            "span": tuple(api.L.d(entity, otype="word")),
        }
        for entity, head in rows
    )


def translation_texts(api) -> dict[str, tuple[dict[str, Any], ...]]:
    """Return English/Arabic translation nodes with their own rendered text."""
    result: dict[str, tuple[dict[str, Any], ...]] = {}
    for otype in ("translation", "arabic_translation"):
        rows = []
        for node in api.F.otype.s(otype):
            rows.append(
                {
                    "node": node,
                    "source_record_id": api.F.source_record_id.v(node),
                    "text": api.T.text(node),
                    "span": tuple(api.L.d(node, otype="word")),
                }
            )
        result[otype] = tuple(rows)
    return result


def document_hits(
    api,
    *,
    corpus: str | None = None,
    dataset: str | None = None,
) -> tuple[tuple[int, ...], ...]:
    """Search physical document nodes by corpus/dataset features."""
    specs = ["document"]
    if corpus is not None:
        _require_node_feature(api, "corpus")
        specs.append(f"corpus={_search_literal(corpus)}")
    if dataset is not None:
        _require_node_feature(api, "dataset")
        specs.append(f"dataset={_search_literal(dataset)}")
    return tuple(api.S.search(" ".join(specs), silent="deep"))


def document_identity(api, document: int) -> dict[str, str | None]:
    """Keep physical source identity separate from scholarly identity."""
    return {
        "physical": api.F.source_record_id.v(document),
        "scholarly": api.F.scholarly_id.v(document)
        if "scholarly_id" in _node_features(api)
        else None,
    }


def relation_pairs(api, relation: str) -> tuple[tuple[int, int], ...]:
    """Search one directed physical-document relation."""
    if relation not in DOCUMENT_RELATIONS:
        raise ValueError(
            f"relation must be one of {sorted(DOCUMENT_RELATIONS)!r}, got {relation!r}"
        )
    _require_edge_feature(api, relation)
    query = f"""\
source:document
target:document
source -{relation}> target
"""
    return tuple(api.S.search(query, silent="deep"))


def render_document(api, document: int) -> dict[str, str | None]:
    """Render generated normalized and, when available, diplomatic text."""
    formats = set(api.T.formats)
    normalized = (
        api.T.text(document, fmt="text-orig-full")
        if "text-orig-full" in formats
        else None
    )
    diplomatic = (
        api.T.text(document, fmt="text-diplomatic-full")
        if "text-diplomatic-full" in formats
        else None
    )
    return {"normalized": normalized, "diplomatic": diplomatic}


def trace_provenance(api, node: int) -> dict[str, str | None]:
    """Trace any measured node/word back to its physical TT record."""
    node_type = api.F.otype.v(node)
    if node_type == "document":
        document = node
    else:
        documents = tuple(api.L.u(node, otype="document"))
        if len(documents) != 1:
            raise ValueError(
                f"expected exactly one physical document for node {node}, got {documents!r}"
            )
        document = documents[0]

    meta = api.TF.features["otype"].metaData
    return {
        "source_record_id": api.F.source_record_id.v(document),
        "scholarly_id": api.F.scholarly_id.v(document)
        if "scholarly_id" in _node_features(api)
        else None,
        "corpus": api.F.corpus.v(document),
        "dataset": api.F.dataset.v(document),
        "source_path": api.F.source_path.v(document),
        "source_sha256": api.F.source_sha256.v(document),
        "packaging": api.F.packaging.v(document),
        "upstream_repository": meta.get("upstreamRepository"),
        "upstream_commit": meta.get("upstreamCommit"),
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tf_dir", type=Path)
    parser.add_argument("--lemma")
    parser.add_argument("--pos")
    parser.add_argument("--func")
    args = parser.parse_args()

    api = load_generated_tf(args.tf_dir)
    payload: dict[str, Any] = {
        "slot_count": api.F.otype.maxSlot,
        "document_count": len(api.F.otype.s("document")),
    }
    if args.lemma is not None:
        payload["lemma_hits"] = lemma_hits(api, args.lemma)
    if args.pos is not None or args.func is not None:
        payload["morphology_hits"] = morphology_hits(
            api, pos=args.pos, func=args.func
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
