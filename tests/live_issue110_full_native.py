"""Full native TF source-language conservation audit on pinned 2,628-record build.

Run immediately after the existing full conversion and reload, sharing its
single remote TT source checkout. Does not publish the data.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from tf.fabric import Fabric

EXPECTED_SLOTS = 2_394_354
EXPECTED_DOCUMENTS = 2_628
EXPECTED_LANGUAGE_NODES = 110_148
EXPECTED_SBL_GREEK = 1_652
EXPECTED_SBL_APPARATUS = 1_095


def main(tf_dir: Path) -> None:
    api = Fabric(locations=[str(tf_dir)], silent="deep").load(
        "value render_mode source_record_id start_char end_char", silent="deep"
    )
    assert api, "real native TF reload unavailable"
    slots = api.F.otype.maxSlot
    documents = len(api.F.otype.s("document"))
    lang = tuple(api.F.otype.s("lang"))
    sbl_greek = len(api.F.otype.s("sbl_greek"))
    sbl_apparatus = len(api.F.otype.s("sbl_apparatus"))
    assert slots == EXPECTED_SLOTS, slots
    assert documents == EXPECTED_DOCUMENTS, documents
    assert len(lang) == EXPECTED_LANGUAGE_NODES, len(lang)
    assert sbl_greek == EXPECTED_SBL_GREEK, sbl_greek
    assert sbl_apparatus == EXPECTED_SBL_APPARATUS, sbl_apparatus

    labels: Counter = Counter()
    modes: Counter = Counter()
    for node in lang:
        label = api.F.value.v(node)
        assert label is not None, f"missing literal source language on node {node}"
        assert api.F.source_record_id.v(node), f"no source record for lang node {node}"
        mode = api.F.render_mode.v(node)
        assert mode in {"lang_anchor", "lang_span"}, (node, mode)
        labels[label] += 1
        modes[mode] += 1
    assert sum(labels.values()) == EXPECTED_LANGUAGE_NODES
    assert all(value > 0 for value in modes.values())
    print(json.dumps({
        "result": "PASS native full Coptic TF source language/SBL preservation",
        "source_records": documents,
        "coptic_word_slots": slots,
        "language_node_count": len(lang),
        "source_language_literal_labels": dict(sorted(labels.items())),
        "lang_boundary_mode_counts": dict(sorted(modes.items())),
        "sbl_greek_nodes": sbl_greek,
        "sbl_apparatus_nodes": sbl_apparatus,
        "semantic_scope": "source annotation only; not Greek NT or LXX lexical equivalence",
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue110_full_native.py NATIVE_TF")
    main(Path(sys.argv[1]))
