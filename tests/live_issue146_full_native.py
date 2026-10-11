"""#146 exact original TT edition reference occurrences versus native TF."""
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
EXPECTED = {
    "chapter_n": 3673,
    "marcion_chapter_n": 403,
    "marcion_verse_n": 10117,
    "petermann_chapter_n": 248,
    "petermann_verse_n": 2320,
}
KINDS = tuple(EXPECTED)
_TAG = re.compile(rb"<(/?)(norm|chapter_n|marcion_chapter_n|marcion_verse_n|petermann_chapter_n|petermann_verse_n)\b([^<>]*)>")


def compare_source_reference_events(source_records, native: dict, *, expected_counts=None):
    """Independently compare every original reference kind/literal/order/word bounds.

    Per-kind source stacks allow crossed wrappers while preserving ordinal
    assignment in *opening* order; norm closings count source Coptic slots.
    Never parse the source using the converter or the native graph builder.
    """
    if expected_counts is None:
        expected_counts = EXPECTED
    seen = set()
    records_seen = set()
    counts = Counter()
    for rid, raw in source_records:
        if not rid or rid.casefold() in records_seen:
            raise ValueError("invalid/duplicate reference source physical record")
        records_seen.add(rid.casefold())
        open_stacks = {kind: [] for kind in KINDS}
        words_closed = 0
        ordinal = 0
        for m in _TAG.finditer(raw):
            closing = bool(m.group(1))
            kind = m.group(2).decode("ascii")
            if kind == "norm":
                if closing:
                    words_closed += 1
                continue
            if not closing:
                ordinal += 1
                attr = re.compile(rb"(?<!\S)" + re.escape(kind.encode("ascii")) + rb"\s*=\s*\"([^\"]*)\"")
                values = attr.findall(m.group(3))
                if len(values) != 1:
                    raise ValueError("reference source missing or duplicated literal")
                value = html.unescape(values[0].decode("utf-8"))
                open_stacks[kind].append((ordinal, value, words_closed))
                continue
            if not open_stacks[kind]:
                raise ValueError(f"reference source orphan closure {kind} at {rid}")
            orig_ordinal, literal, start_after = open_stacks[kind].pop()
            key = (rid, orig_ordinal)
            if key in seen:
                raise ValueError("duplicate reference source occurrence")
            seen.add(key)
            if native.get(key) != (kind, literal, start_after, words_closed):
                raise ValueError(f"reference native value/word bounds mismatch at {key!r}")
            counts[kind] += 1
        if any(open_stacks.values()):
            raise ValueError(f"unclosed original edition reference {rid}")
    if seen != set(native):
        raise ValueError("original reference/source TF occurrence parity mismatch")
    if dict(counts) != expected_counts:
        raise ValueError(f"reference source tag inventory changed: {counts}")
    return dict(sorted(counts.items()))


def main(tf_root: Path, source_root: Path):
    api = Fabric(locations=[str(tf_root)], silent="deep").load(
        "value render_mode source_record_id source_ordinal "
        "start_word_ordinal start_char start_after_word_ordinal "
        "end_word_ordinal end_char end_after_word_ordinal",
        silent="deep",
    )
    assert api and api.F.otype.maxSlot == 2394354
    assert len(api.F.otype.s("document")) == 2628
    assert len(api.F.otype.s("lang")) == 110148
    assert len(api.F.otype.s("sbl_greek")) == 1652
    assert len(api.F.otype.s("sbl_apparatus")) == 1095
    assert len(api.F.otype.s("morph")) == 78265
    assert len(api.F.otype.s("multiword")) == 35148
    for kind, expected in (
        ("ed_line_n",42189),("ed_lb_n",216),("ed_page_n",1047),("ed_pg_n",283)
    ):
        assert len(api.F.otype.s(kind)) == expected
    native = {}
    modes = Counter()
    for kind, count in EXPECTED.items():
        nodes = api.F.otype.s(kind)
        assert len(nodes) == count, (kind,len(nodes),count)
        for n in nodes:
            key = (api.F.source_record_id.v(n),api.F.source_ordinal.v(n))
            assert key[0] and isinstance(key[1],int) and key not in native, key
            literal = api.F.value.v(n)
            assert literal is not None, key
            mode = api.F.render_mode.v(n)
            assert mode in ("reference_span","reference_anchor"), (kind,mode)
            slots = api.E.oslots.s(n)
            assert len(slots)>=1
            if mode=="reference_anchor":
                assert len(slots)==1
            start = api.F.start_after_word_ordinal.v(n)
            end = api.F.end_after_word_ordinal.v(n)
            assert isinstance(start,int) and isinstance(end,int) and 0<=start<=end
            for word,char in (
                (api.F.start_word_ordinal.v(n),api.F.start_char.v(n)),
                (api.F.end_word_ordinal.v(n),api.F.end_char.v(n)),
            ):
                assert (word is None)==(char is None), (key,word,char)
            native[key] = (kind,literal,start,end)
            modes[(kind,mode)] += 1
    counts = compare_source_reference_events(
        ((rid,raw) for rid,_path,raw,_packaging in records(source_root)),
        native,
    )
    print(json.dumps({
        "status":"PASS source-exact edition reference chapter/verse wrappers",
        "source_pin":PIN,
        "nodes_by_kind":counts,
        "source_word_slots":api.F.otype.maxSlot,
        "exact_original_kind_literal_ordinal_word_boundary_parity":True,
        "modes":{"|".join(k):v for k,v in sorted(modes.items())},
    },sort_keys=True),flush=True)


if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("usage: python tests/live_issue146_full_native.py TF_DIR TT_ROOT")
    main(Path(sys.argv[1]),Path(sys.argv[2]))
