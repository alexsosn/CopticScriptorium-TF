"""#143 complete pinned TT -> native TF multiword source-literal conservation."""
from __future__ import annotations

from collections import Counter
import html
import json
from pathlib import Path
import re
import sys

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.sbl_source_census import records

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
EXPECTED = 35_148
_MULTIWORD_TAG = re.compile(rb"<multiword\b([^<>]*)>")
_MULTIWORD_VALUE = re.compile(rb'(?<!\S)multiword="([^"]*)"')


def compare_pinned_multiword_literals(source_records, native: dict) -> int:
    """Compare *each original* opening literal and ordinal, not just tag totals.

    Source scan neither imports parse_tt_record nor uses model annotations.
    Both directory and ZIP TT physical records are separately keyed.
    """
    seen: set[tuple[str, int]] = set()
    physical: set[str] = set()
    for record_id, raw in source_records:
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("multiword physical source identity missing")
        if record_id.casefold() in physical:
            raise ValueError("duplicate multiword physical source record")
        physical.add(record_id.casefold())
        ordinal = 0
        for match in _MULTIWORD_TAG.finditer(raw):
            ordinal += 1
            values = _MULTIWORD_VALUE.findall(match.group(1))
            if len(values) != 1:
                raise ValueError("multiword missing or duplicated original literal")
            literal = html.unescape(values[0].decode("utf-8"))
            key = (record_id, ordinal)
            if key in seen:
                raise ValueError("duplicate multiword source opening")
            seen.add(key)
            if native.get(key) != literal:
                raise ValueError(f"multiword original literal/ordinal mismatch at {key!r}")
    if seen != set(native):
        raise ValueError("multiword original source-to-native occurrence mismatch")
    return len(seen)


_POSITION_TAG = re.compile(rb"<(/?)(norm|multiword)\b([^<>]*)>")


def compare_pinned_multiword_spans(source_records, native: dict) -> int:
    """Independent raw TT event scanner: literal and exact word-close bounds.

    This uses neither parse_tt_record nor the graph builder or TF writer.
    Crossing layout, translation, and edition tags are ignored deliberately;
    each original closing norm represents one completed source Coptic word.
    """
    seen: set[tuple[str, int]] = set()
    physical: set[str] = set()
    for rid, raw in source_records:
        if not isinstance(rid, str) or not rid:
            raise ValueError("multiword source identity missing")
        if rid.casefold() in physical:
            raise ValueError("duplicate multiword physical source record")
        physical.add(rid.casefold())
        closed_norms = 0
        opening = 0
        stack: list[tuple[tuple[str, int], str, int]] = []
        for m in _POSITION_TAG.finditer(raw):
            closing, kind, attrs = m.groups()
            if kind == b"norm":
                if closing:
                    closed_norms += 1
                continue
            if not closing:
                opening += 1
                values = _MULTIWORD_VALUE.findall(attrs)
                if len(values) != 1:
                    raise ValueError("multiword missing/duplicated source literal")
                literal = html.unescape(values[0].decode("utf-8"))
                stack.append(((rid, opening), literal, closed_norms))
                continue
            if not stack:
                raise ValueError("multiword closing without opening")
            key, literal, start_after = stack.pop()
            if key in seen:
                raise ValueError("duplicate multiword opening ordinal")
            seen.add(key)
            expected = (literal, start_after, closed_norms)
            if native.get(key) != expected:
                raise ValueError(
                    f"multiword source literal/boundary differs from native TF at {key!r}"
                )
        if stack:
            raise ValueError(f"multiword unclosed source event in {rid}")
    if seen != set(native):
        raise ValueError("multiword source/native opening count differs")
    return len(seen)


def main(tf_root: Path, source_root: Path) -> None:
    api = Fabric(locations=[str(tf_root)], silent="deep").load(
        "value render_mode source_record_id source_ordinal "
        "start_word_ordinal start_char start_after_word_ordinal "
        "end_word_ordinal end_char end_after_word_ordinal",
        silent="deep",
    )
    assert api, "could not reload Text-Fabric"
    assert api.F.otype.maxSlot == 2_394_354
    assert len(api.F.otype.s("document")) == 2_628
    assert len(api.F.otype.s("lang")) == 110_148
    assert len(api.F.otype.s("sbl_greek")) == 1_652
    assert len(api.F.otype.s("sbl_apparatus")) == 1_095
    assert len(api.F.otype.s("morph")) == 78_265
    for name, count in (("ed_line_n", 42_189), ("ed_lb_n", 216),
                        ("ed_page_n", 1_047), ("ed_pg_n", 283)):
        assert len(api.F.otype.s(name)) == count, (name, count)
    nodes = api.F.otype.s("multiword")
    assert len(nodes) == EXPECTED, (len(nodes), EXPECTED)
    by_mode = Counter()
    native: dict[tuple[str, int], str] = {}
    native_spans: dict[tuple[str, int], tuple[str, int, int]] = {}
    for n in nodes:
        rid = api.F.source_record_id.v(n)
        ordinal = api.F.source_ordinal.v(n)
        literal = api.F.value.v(n)
        mode = api.F.render_mode.v(n)
        assert isinstance(rid, str) and rid and isinstance(ordinal, int)
        assert isinstance(literal, str)
        assert mode in ("multiword_span", "multiword_anchor")
        key = (rid, ordinal)
        assert key not in native, f"duplicate multiword native occurrence {key!r}"
        native[key] = literal
        native_spans[key] = (
            literal,
            api.F.start_after_word_ordinal.v(n),
            api.F.end_after_word_ordinal.v(n),
        )
        slots = api.E.oslots.s(n)
        assert len(slots) >= 1
        if mode == "multiword_anchor":
            assert len(slots) == 1
        else:
            assert list(slots) == list(range(slots[0], slots[-1] + 1))
        start = api.F.start_after_word_ordinal.v(n)
        end = api.F.end_after_word_ordinal.v(n)
        assert isinstance(start, int) and isinstance(end, int) and start <= end
        for word, char in (
            (api.F.start_word_ordinal.v(n), api.F.start_char.v(n)),
            (api.F.end_word_ordinal.v(n), api.F.end_char.v(n)),
        ):
            assert (word is None) == (char is None), (key, word, char)
        by_mode[mode] += 1
    assert compare_pinned_multiword_spans(
        ((ident, raw) for ident, _path, raw, _pack in records(source_root)), native_spans
    ) == EXPECTED
    print(json.dumps({
        "status": "PASS exact native multiword grouping source conservation",
        "upstream_revision": PIN,
        "words": api.F.otype.maxSlot,
        "physical_source_records": 2628,
        "multiword_nodes": EXPECTED,
        "opening_kind_literal_ordinal_parity": True,
        "independent_original_tt_start_end_word_boundary_parity": True,
        "modes": dict(sorted(by_mode.items())),
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue143_full_native.py TF_DIR PINNED_TT_ROOT")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
