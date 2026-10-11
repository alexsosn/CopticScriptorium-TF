"""#135 exact-source full native token wrapper conservation release gate.

Called on output of the existing *single* pinned corpus conversion/reload job;
does not fetch or copy upstream corpus data. Contrasts independently observed
raw source opening-tag count with reloaded TF annotation nodes.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from tf.fabric import Fabric

EXPECTED = {
    "morph": 78_265,
    "norm_func": 20_011,
    "norm_head": 17_713,
    "norm_xml:id": 20_011,
    "norm_new_sent": 860,
}


def main(tf_dir: Path) -> None:
    api = Fabric(locations=[str(tf_dir)], silent="deep").load(
        "value render_mode source_record_id source_ordinal start_word_ordinal "
        "start_char start_after_word_ordinal end_word_ordinal end_char "
        "end_after_word_ordinal",
        silent="deep",
    )
    assert api, "native Text-Fabric reload failed"
    assert api.F.otype.maxSlot == 2_394_354, api.F.otype.maxSlot
    assert len(api.F.otype.s("document")) == 2_628
    assert len(api.F.otype.s("lang")) == 110_148
    assert len(api.F.otype.s("sbl_greek")) == 1_652
    assert len(api.F.otype.s("sbl_apparatus")) == 1_095
    observed = Counter()
    identity: set[tuple[str, int]] = set()
    examples = Counter()
    for kind, expected_count in EXPECTED.items():
        nodes = api.F.otype.s(kind)
        assert len(nodes) == expected_count, (kind, len(nodes), expected_count)
        for node in nodes:
            source_record_id = api.F.source_record_id.v(node)
            ordinal = api.F.source_ordinal.v(node)
            assert source_record_id and isinstance(ordinal, int), (kind, node)
            key = (source_record_id, ordinal)
            assert key not in identity, f"token source ordinal collision: {key!r}"
            identity.add(key)
            assert api.F.value.v(node) is not None, (kind, node)
            assert api.F.render_mode.v(node) == "token_annotation_anchor", (kind, node)
            start_word = api.F.start_word_ordinal.v(node)
            end_word = api.F.end_word_ordinal.v(node)
            start = api.F.start_char.v(node)
            end = api.F.end_char.v(node)
            assert start_word and start_word == end_word, (kind, node)
            assert isinstance(start, int) and isinstance(end, int)
            assert 0 <= start <= end, (kind, node, start, end)
            assert api.F.start_after_word_ordinal.v(node) == start_word - 1
            assert api.F.end_after_word_ordinal.v(node) == start_word - 1
            assert len(api.E.oslots.s(node)) == 1, (kind, node)
            observed[kind] += 1
            if source_record_id in {
                "AP/apophthegmata.patrum:AP.001.n135.mother",
                "proclus-homilies/proclus.homilies:proclus.23.nativity",
            }:
                examples[(source_record_id, kind)] += 1
    assert observed == EXPECTED, (observed, EXPECTED)
    assert sum(observed.values()) == 136_860
    assert examples[("AP/apophthegmata.patrum:AP.001.n135.mother", "morph")] > 0
    assert examples[("proclus-homilies/proclus.homilies:proclus.23.nativity", "norm_func")] > 0
    print(json.dumps({
        "result": "PASS source-exact native TT token wrapper conservation",
        "pinned_source": "CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5",
        "nodes_by_type": dict(sorted(observed.items())),
        "all_source_ordinals_unique_per_record": True,
        "word_slots": api.F.otype.maxSlot,
        "physical_documents": len(api.F.otype.s("document")),
        "example_counts": {"|".join(key): value for key, value in sorted(examples.items())},
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue135_full_native.py TF_DIR")
    main(Path(sys.argv[1]))
