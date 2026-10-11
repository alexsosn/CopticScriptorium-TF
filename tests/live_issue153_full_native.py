"""#153 independently compare pinned editorial TT evidence to native Text-Fabric."""
from __future__ import annotations

from collections import Counter
from html import unescape
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
EXPECTED = {
    "hi_rend": 5172, "note": 2822, "gap_reason": 1079,
    "supplied_reason": 815, "note_note": 333, "gap_unit": 170,
    "supplied_source": 99, "gap_quantity": 94, "gap_extent": 75,
    "supplied_evidence": 67, "unclear_reason": 64, "unclear": 27,
}
_TAG = re.compile(
    rb"<(/?)(norm|hi_rend|note|gap_reason|supplied_reason|note_note|"
    rb"gap_unit|supplied_source|gap_quantity|gap_extent|"
    rb"supplied_evidence|unclear_reason|unclear)\b([^<>]*)>"
)


def compare_source_editorial_events(source_records, native: dict, *, expected_counts=None):
    """Independent byte-level TT scanner, not parser or native graph.

    Tracks source-open ordered identity, attribute value, completed norm word
    positions on both boundaries across independent per-kind SGML stacks.
    """
    if expected_counts is None:
        expected_counts = EXPECTED
    seen = set()
    seen_records = set()
    counts = Counter()
    for rid, raw in source_records:
        if not isinstance(rid, str) or not rid or rid.casefold() in seen_records:
            raise ValueError("invalid/duplicate editorial source physical record")
        seen_records.add(rid.casefold())
        opened = 0
        closed_words = 0
        stacks = {kind: [] for kind in EXPECTED}
        for m in _TAG.finditer(raw):
            closing, label, attrs = m.groups()
            kind = label.decode("ascii")
            if kind == "norm":
                if closing:
                    closed_words += 1
                continue
            if not closing:
                opened += 1
                attr_re = re.compile(
                    rb'(?<!\S)' + re.escape(label) + rb'\s*=\s*"([^"]*)"'
                )
                values = attr_re.findall(attrs)
                if len(values) != 1:
                    raise ValueError("editorial source missing/duplicated literal")
                stacks[kind].append((opened, unescape(values[0].decode("utf-8")), closed_words))
                continue
            if not stacks[kind]:
                raise ValueError("editorial source closing without opening")
            ordinal, literal, start = stacks[kind].pop()
            key = (rid, ordinal)
            if key in seen:
                raise ValueError("duplicate editorial source opening ordinal")
            seen.add(key)
            if native.get(key) != (kind, literal, start, closed_words):
                raise ValueError("editorial native original kind/value/word boundary mismatch")
            counts[kind] += 1
        if any(stacks.values()):
            raise ValueError("unclosed editorial source annotation")
    if seen != set(native):
        raise ValueError("editorial source/native occurrence mismatch")
    if dict(counts) != expected_counts:
        raise ValueError(f"editorial source inventory changed: {dict(counts)}")
    return dict(sorted(counts.items()))


def main(tf_root: Path, source_root: Path) -> None:
    api = Fabric(locations=[str(tf_root)], silent="deep").load(
        "value render_mode source_record_id source_ordinal "
        "start_word_ordinal start_char start_after_word_ordinal "
        "end_word_ordinal end_char end_after_word_ordinal",
        silent="deep",
    )
    assert api, "native TF reload failed"
    assert api.F.otype.maxSlot == 2_394_354
    assert len(api.F.otype.s("document")) == 2_628
    for name, expected in {
        "lang": 110148, "sbl_greek": 1652, "sbl_apparatus": 1095,
        "morph": 78265, "multiword": 35148,
        "ed_line_n": 42189, "ed_lb_n": 216,
        "ed_page_n": 1047, "ed_pg_n": 283,
        "chapter_n": 3673, "marcion_chapter_n": 403,
        "marcion_verse_n": 10117, "petermann_chapter_n": 248,
        "petermann_verse_n": 2320,
    }.items():
        assert len(api.F.otype.s(name)) == expected, (name, expected)
    native = {}
    modes = Counter()
    for kind, count in EXPECTED.items():
        nodes = api.F.otype.s(kind)
        assert len(nodes) == count, (kind,len(nodes),count)
        for n in nodes:
            key = (api.F.source_record_id.v(n), api.F.source_ordinal.v(n))
            assert isinstance(key[0], str) and key[0] and isinstance(key[1], int)
            assert key not in native, (kind,key)
            value = api.F.value.v(n)
            mode = api.F.render_mode.v(n)
            assert isinstance(value, str)
            assert mode in ("editorial_span", "editorial_anchor"), (kind,mode)
            slots = api.E.oslots.s(n)
            assert len(slots) >= 1
            if mode == "editorial_anchor":
                assert len(slots) == 1
            start, end = (
                api.F.start_after_word_ordinal.v(n),
                api.F.end_after_word_ordinal.v(n),
            )
            assert isinstance(start, int) and isinstance(end, int) and 0 <= start <= end
            for word,char in (
                (api.F.start_word_ordinal.v(n),api.F.start_char.v(n)),
                (api.F.end_word_ordinal.v(n),api.F.end_char.v(n)),
            ):
                assert (word is None) == (char is None)
            native[key] = (kind,value,start,end)
            modes[(kind,mode)] += 1
    assert len(native) == sum(EXPECTED.values()) == 10817
    parity = compare_source_editorial_events(
        ((rid, raw) for rid,_path,raw,_pack in records(source_root)),
        native,
    )
    print(json.dumps({
        "result": "PASS independent editorial original TT/native TF exact source parity",
        "source_revision": PIN,
        "original_source_records": 2628,
        "nodes_by_kind": parity,
        "total_editorial_source_events": len(native),
        "source_kind_literal_opening_ordinal_word_boundaries_exact": True,
        "modes": {"|".join(k): v for k,v in sorted(modes.items())},
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue153_full_native.py TF_DIR TT_ROOT")
    main(Path(sys.argv[1]),Path(sys.argv[2]))
