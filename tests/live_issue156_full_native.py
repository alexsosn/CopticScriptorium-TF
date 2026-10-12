"""#156 independent original source multi-attr gap/supplied/abbr vs native TF."""
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
EXPECTED = {"gap": 1162, "supplied": 1865, "abbr": 1620}
ATTRS = {
    "gap": ("extent","gap","reason","unit"),
    "supplied": ("reason","source","supplied"),
    "abbr": ("type",),
}
_TAG = re.compile(rb"<(/?)(norm|gap|supplied|abbr)\b([^<>]*)>")
_ATTRIBUTE = re.compile(rb'\s+([A-Za-z_][A-Za-z0-9_.:-]*)\s*=\s*"([^"]*)"')


def _attrs(raw: bytes, kind: str) -> tuple[tuple[str, str], ...]:
    pos = 0
    result = {}
    while pos < len(raw):
        if not raw[pos:].strip():
            break
        m = _ATTRIBUTE.match(raw, pos)
        if m is None:
            raise ValueError("malformed intervention source attributes")
        key = m.group(1).decode("ascii")
        if key in result or key not in ATTRS[kind]:
            raise ValueError("duplicate/unknown intervention source attribute")
        result[key] = unescape(m.group(2).decode("utf-8"))
        pos = m.end()
    if not result:
        raise ValueError("intervention source has no literal attributes")
    return tuple(sorted(result.items()))


def compare_source_interventions(source_records, native, *, expected_counts=None):
    """Independently check ALL original attrs + original word boundaries."""
    if expected_counts is None:
        expected_counts = EXPECTED
    seen = set()
    physical = set()
    counts = Counter()
    for rid, raw in source_records:
        if not rid or rid.casefold() in physical:
            raise ValueError("missing/duplicate intervention source physical record")
        physical.add(rid.casefold())
        stacks = {kind: [] for kind in EXPECTED}
        closed_norms = 0
        ordinal = 0
        for m in _TAG.finditer(raw):
            closing, kind_b, attr_b = m.groups()
            kind = kind_b.decode("ascii")
            if kind == "norm":
                if closing:
                    closed_norms += 1
                continue
            if not closing:
                ordinal += 1
                stacks[kind].append((ordinal, _attrs(attr_b, kind), closed_norms))
                continue
            if not stacks[kind]:
                raise ValueError("intervention closing without original opening")
            opened, attrs, start_after = stacks[kind].pop()
            key = (rid, opened)
            if key in seen:
                raise ValueError("duplicate intervention original source ordinal")
            seen.add(key)
            attr_dict = dict(attrs)
            primary = attr_dict.get("type", "") if kind == "abbr" else attr_dict.get(kind,"")
            expected = (kind, primary, attrs, start_after, closed_norms)
            if native.get(key) != expected:
                raise ValueError(f"intervention source/native literal attrs/word bounds mismatch at {key!r}")
            counts[kind] += 1
        if any(stacks.values()):
            raise ValueError("unclosed original intervention source event")
    if seen != set(native):
        raise ValueError("intervention source/native occurrence mismatch")
    if dict(counts) != expected_counts:
        raise ValueError(f"intervention source inventory drift: {dict(counts)}")
    return dict(sorted(counts.items()))


def main(tf_root: Path, source_root: Path) -> None:
    all_features = [
        f"source_attr_{kind}_{key}" for kind, keys in ATTRS.items() for key in keys
    ]
    api = Fabric(locations=[str(tf_root)], silent="deep").load(
        "value render_mode source_record_id source_ordinal "
        "start_word_ordinal start_char start_after_word_ordinal "
        "end_word_ordinal end_char end_after_word_ordinal " + " ".join(all_features),
        silent="deep",
    )
    assert api and api.F.otype.maxSlot == 2394354
    assert len(api.F.otype.s("document")) == 2628
    assert len(api.F.otype.s("lang")) == 110148
    assert len(api.F.otype.s("sbl_greek")) == 1652
    assert len(api.F.otype.s("sbl_apparatus")) == 1095
    for kind, expected in (
        ("morph",78265),("multiword",35148),("ed_line_n",42189),
        ("ed_lb_n",216),("ed_page_n",1047),("ed_pg_n",283),
        ("chapter_n",3673),("marcion_chapter_n",403),
        ("marcion_verse_n",10117),("petermann_chapter_n",248),
        ("petermann_verse_n",2320),("hi_rend",5172),("note",2822),
        ("gap_reason",1079),("supplied_reason",815),("note_note",333),
        ("gap_unit",170),("supplied_source",99),("gap_quantity",94),
        ("gap_extent",75),("supplied_evidence",67),("unclear_reason",64),
        ("unclear",27),
    ):
        assert len(api.F.otype.s(kind)) == expected, (kind,expected)
    native = {}
    modes = Counter()
    for kind, n_expected in EXPECTED.items():
        nodes = api.F.otype.s(kind)
        assert len(nodes) == n_expected, (kind,len(nodes),n_expected)
        for n in nodes:
            key = (api.F.source_record_id.v(n),api.F.source_ordinal.v(n))
            assert key[0] and isinstance(key[1],int) and key not in native
            value = api.F.value.v(n)
            assert isinstance(value,str)
            pairs = []
            for attr in ATTRS[kind]:
                v = getattr(api.F,f"source_attr_{kind}_{attr}").v(n)
                if v is not None:
                    assert isinstance(v,str)
                    pairs.append((attr,v))
            assert pairs
            attr_tuple = tuple(sorted(pairs))
            mode = api.F.render_mode.v(n)
            assert mode in ("intervention_span","intervention_anchor")
            slots = api.E.oslots.s(n)
            assert len(slots)>=1
            if mode=="intervention_anchor":
                assert len(slots)==1
            start = api.F.start_after_word_ordinal.v(n)
            end = api.F.end_after_word_ordinal.v(n)
            assert isinstance(start,int) and isinstance(end,int) and 0<=start<=end
            for word,char in (
                (api.F.start_word_ordinal.v(n),api.F.start_char.v(n)),
                (api.F.end_word_ordinal.v(n),api.F.end_char.v(n)),
            ):
                assert (word is None)==(char is None)
            native[key] = (kind,value,attr_tuple,start,end)
            modes[(kind,mode)] += 1
    assert len(native) == 4647
    parity = compare_source_interventions(
        ((rid,raw) for rid,_path,raw,_pack in records(source_root)),
        native,
    )
    print(json.dumps({
        "result": "PASS lossless native source gap/supplied/abbr attribute conservation",
        "source_revision": PIN,
        "source_records": 2628,
        "word_slots": 2394354,
        "source_counts": parity,
        "original_attribute_literal_presence_and_word_boundary_parity": True,
        "modes": {"|".join(k):v for k,v in sorted(modes.items())},
    },sort_keys=True),flush=True)


if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("usage: python tests/live_issue156_full_native.py TF_DIR TT_ROOT")
    main(Path(sys.argv[1]),Path(sys.argv[2]))
