"""#140 edition pagination native TF acceptance on complete pinned TT checkout."""
from __future__ import annotations

from collections import Counter
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tf.fabric import Fabric

from copticscriptorium_tf.sbl_source_census import records

EXPECTED = {
    "ed_line_n": 42_189,
    "ed_lb_n": 216,
    "ed_page_n": 1_047,
    "ed_pg_n": 283,
}



_EDITION_TAG = re.compile(rb'<(ed_line_n|ed_lb_n|ed_page_n|ed_pg_n)\b([^<>]*)>')


def compare_pinned_edition_literals(source_records, native: dict) -> dict[str, int]:
    """Independently compare EVERY raw TT opening value/kind/ordinal to native TF.

    This reader does not call the Coptic TT parser or graph writer. It counts
    each TT archive member and directory file as a distinct physical source
    record. Only categorical counts are returned; no licensed source text.
    """
    counts: Counter[str] = Counter()
    observed: set[tuple[str, int]] = set()
    physical: set[str] = set()
    for record_id, raw in source_records:
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("invalid edition physical source identity")
        if record_id.casefold() in physical:
            raise ValueError("duplicate edition physical source record")
        physical.add(record_id.casefold())
        ordinal = 0
        for match in _EDITION_TAG.finditer(raw):
            ordinal += 1
            kind = match.group(1).decode("ascii")
            attr = re.compile(rb'(?<!\S)' + re.escape(match.group(1)) + rb'="([^"]*)"')
            values = attr.findall(match.group(2))
            if len(values) != 1:
                raise ValueError("edition opening missing or duplicated original literal")
            literal = values[0].decode("utf-8")
            key = (record_id, ordinal)
            if key in observed:
                raise ValueError("duplicate edition source occurrence")
            observed.add(key)
            target = native.get(key)
            if target is None:
                raise ValueError("edition native TF missing original occurrence")
            if target != (kind, literal):
                raise ValueError("edition kind/value differs from original source")
            counts[kind] += 1
    if observed != set(native):
        raise ValueError("edition source-to-native occurrence parity mismatch")
    return dict(sorted(counts.items()))

def main(tf_root: Path, source_root: Path | None = None) -> None:
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
    native: dict[tuple[str, int], tuple[str, str]] = {}
    for tag, count in EXPECTED.items():
        nodes = api.F.otype.s(tag)
        assert len(nodes) == count, (tag, len(nodes), count)
        for n in nodes:
            key = (api.F.source_record_id.v(n), api.F.source_ordinal.v(n))
            assert key[0] and isinstance(key[1], int)
            assert key not in unique, (tag, key)
            unique.add(key)
            assert api.F.value.v(n) is not None
            native[key] = (tag, api.F.value.v(n))
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
    raw_parity = None
    if source_root is not None:
        raw_parity = compare_pinned_edition_literals(
            ((identity, payload) for identity, _path, payload, _pack in records(source_root)),
            native,
        )
        if raw_parity != EXPECTED:
            raise ValueError("complete edition original TT to native value/count drift")
    print(json.dumps({
        "result": "PASS exact native edition source annotation coverage",
        "source_revision": "3ac067f1709a0012daf39ea8da2fac79980176a5",
        "word_slots": api.F.otype.maxSlot,
        "nodes_by_type": EXPECTED,
        "modes": {"|".join(k): v for k, v in sorted(modes.items())},
        "unique_per_record_opening_ordinals": True,
        "independent_exact_original_tt_literals": raw_parity,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: python tests/live_issue140_full_native.py TF_DIR [PINNED_TT_ROOT]")
    main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) == 3 else None)
