"""#140 edition pagination native TF acceptance on complete pinned TT checkout."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from tf.fabric import Fabric

EXPECTED = {
    "ed_line_n": 42_189,
    "ed_lb_n": 216,
    "ed_page_n": 1_047,
    "ed_pg_n": 283,
}


def main(tf_root: Path) -> None:
    api = Fabric(locations=[str(tf_root)], silent="deep").load(
        "value render_mode source_record_id source_ordinal "
        "start_word_ordinal start_char start_after_word_ordinal "
        "end_word_ordinal end_char end_after_word_ordinal",
        silent="deep",
    )
    assert api, "native TF reload failed"
    assert api.F.otype.maxSlot == 2_394_354
    assert len(api.F.otype.s("document")) == 2_628
    assert len(api.F.otype.s("lang")) == 110_148
    assert len(api.F.otype.s("sbl_greek")) == 1_652
    assert len(api.F.otype.s("sbl_apparatus")) == 1_095
    assert len(api.F.otype.s("morph")) == 78_265
    unique: set[tuple[str, int]] = set()
    modes = Counter()
    for tag, count in EXPECTED.items():
        nodes = api.F.otype.s(tag)
        assert len(nodes) == count, (tag, len(nodes), count)
        for n in nodes:
            key = (api.F.source_record_id.v(n), api.F.source_ordinal.v(n))
            assert key[0] and isinstance(key[1], int)
            assert key not in unique, (tag, key)
            unique.add(key)
            assert api.F.value.v(n) is not None
            mode = api.F.render_mode.v(n)
            assert mode in {"edition_span", "edition_anchor"}, (tag, n, mode)
            assert len(api.E.oslots.s(n)) >= 1
            if mode == "edition_anchor":
                assert len(api.E.oslots.s(n)) == 1
            start = api.F.start_after_word_ordinal.v(n)
            end = api.F.end_after_word_ordinal.v(n)
            assert isinstance(start, int) and isinstance(end, int) and start <= end
            for a,b in [(api.F.start_word_ordinal.v(n), api.F.start_char.v(n)),
                        (api.F.end_word_ordinal.v(n), api.F.end_char.v(n))]:
                assert (a is None) == (b is None), (tag, n, a, b)
            modes[(tag, mode)] += 1
    assert len(unique) == sum(EXPECTED.values()) == 43_735
    print(json.dumps({
        "result": "PASS exact native edition source annotation coverage",
        "source_revision": "3ac067f1709a0012daf39ea8da2fac79980176a5",
        "word_slots": api.F.otype.maxSlot,
        "nodes_by_type": EXPECTED,
        "modes": {"|".join(k): v for k, v in sorted(modes.items())},
        "unique_per_record_opening_ordinals": True,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue140_full_native.py TF_DIR")
    main(Path(sys.argv[1]))
