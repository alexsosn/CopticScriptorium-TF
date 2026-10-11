"""#159 independent pinned original TT entity/name label source-to-native parity."""
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
    sys.path.insert(0,str(ROOT))

from copticscriptorium_tf.sbl_source_census import records

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
EXPECTED = {
    "entity_head_tok": 3677, "entity_text": 3677,
    "entity_identity": 901, "persName_type": 245,
    "placeName_type": 140, "placeName_ref": 85,
    "roleName_type": 80, "rs_type": 18, "org_type": 4,
}
_TAG = re.compile(
    rb"<(/?)(norm|entity_head_tok|entity_text|entity_identity|"
    rb"persName_type|placeName_type|placeName_ref|roleName_type|"
    rb"rs_type|org_type)\b([^<>]*)>"
)


def compare_source_entity_labels(source_records, native, *, expected_counts=None):
    """Independent byte scanner: original kind, exact label, opening, word bounds."""
    if expected_counts is None:
        expected_counts = EXPECTED
    source_set = set()
    physical_seen = set()
    counts = Counter()
    for rid, raw in source_records:
        if not rid or rid.casefold() in physical_seen:
            raise ValueError("entity label source record identity invalid or duplicated")
        physical_seen.add(rid.casefold())
        ordinal = 0
        closed_words = 0
        stacks = {kind: [] for kind in EXPECTED}
        for match in _TAG.finditer(raw):
            closing, kind_bytes, attrs = match.groups()
            kind = kind_bytes.decode("ascii")
            if kind == "norm":
                if closing:
                    closed_words += 1
                continue
            if not closing:
                ordinal += 1
                pat = re.compile(
                    rb'(?<!\S)' + re.escape(kind_bytes) + rb'\s*=\s*"([^"]*)"'
                )
                values = pat.findall(attrs)
                if len(values) != 1:
                    raise ValueError("entity label source missing or duplicate literal")
                stacks[kind].append((ordinal, unescape(values[0].decode("utf-8")), closed_words))
                continue
            if not stacks[kind]:
                raise ValueError("entity label closing without opening")
            original_ordinal, label, start = stacks[kind].pop()
            key = (rid, original_ordinal)
            if key in source_set:
                raise ValueError("duplicate entity label source ordinal")
            source_set.add(key)
            if native.get(key) != (kind, label, start, closed_words):
                raise ValueError(f"entity label original TT/native source mismatch at {key!r}")
            counts[kind] += 1
        if any(stacks.values()):
            raise ValueError("unclosed entity label original source wrapper")
    if source_set != set(native):
        raise ValueError("entity label native/original source event inventory mismatch")
    if dict(counts) != expected_counts:
        raise ValueError(f"entity label source kinds changed: {dict(counts)}")
    return dict(sorted(counts.items()))


def main(tf_root: Path, source_root: Path):
    api = Fabric(locations=[str(tf_root)],silent="deep").load(
        "value render_mode source_record_id source_ordinal "
        "start_word_ordinal start_char start_after_word_ordinal "
        "end_word_ordinal end_char end_after_word_ordinal",
        silent="deep",
    )
    assert api and api.F.otype.maxSlot == 2394354
    assert len(api.F.otype.s("document")) == 2628
    for kind, n in {
        "lang":110148, "sbl_greek":1652, "sbl_apparatus":1095,
        "morph":78265, "multiword":35148, "ed_line_n":42189,
        "ed_lb_n":216,"ed_page_n":1047,"ed_pg_n":283,
        "chapter_n":3673, "marcion_chapter_n":403,"marcion_verse_n":10117,
        "petermann_chapter_n":248,"petermann_verse_n":2320,
        "hi_rend":5172,"note":2822,"gap_reason":1079,"supplied_reason":815,
        "note_note":333,"gap_unit":170,"supplied_source":99,
        "gap_quantity":94,"gap_extent":75,"supplied_evidence":67,
        "unclear_reason":64,"unclear":27,
        "gap":1162,"supplied":1865,"abbr":1620,
    }.items():
        assert len(api.F.otype.s(kind)) == n, (kind,n)
    native = {}
    modes = Counter()
    for kind, expected in EXPECTED.items():
        nodes = api.F.otype.s(kind)
        assert len(nodes) == expected,(kind,len(nodes),expected)
        for n in nodes:
            key=(api.F.source_record_id.v(n),api.F.source_ordinal.v(n))
            if not key[0] or not isinstance(key[1],int) or key in native:
                raise ValueError(f"duplicate/missing native entity source identity {key}")
            value=api.F.value.v(n)
            assert isinstance(value,str), key
            mode=api.F.render_mode.v(n)
            assert mode in ("entity_label_span","entity_label_anchor"), (kind,mode)
            slots=api.E.oslots.s(n)
            assert len(slots)>=1, (key,"missing word locus")
            if mode == "entity_label_anchor":
                assert len(slots)==1, (key,slots)
            start,end=api.F.start_after_word_ordinal.v(n),api.F.end_after_word_ordinal.v(n)
            assert isinstance(start,int) and isinstance(end,int) and 0<=start<=end
            for word,char in (
                (api.F.start_word_ordinal.v(n),api.F.start_char.v(n)),
                (api.F.end_word_ordinal.v(n),api.F.end_char.v(n)),
            ):
                assert (word is None)==(char is None)
            native[key]=(kind,value,start,end)
            modes[(kind,mode)]+=1
    assert len(native)==8827
    source_counts=compare_source_entity_labels(
        ((rid,raw) for rid,_path,raw,_pack in records(source_root)),native
    )
    print(json.dumps({
        "result":"PASS independent 8827 entity/name source literal and word-boundary parity",
        "source_revision":PIN,
        "source_records":2628,
        "slots":2394354,
        "nodes_by_type":source_counts,
        "original_label_kind_literal_ordinal_word_boundary_parity":True,
        "modes":{"|".join(k):v for k,v in sorted(modes.items())},
    },sort_keys=True),flush=True)


if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("usage: python tests/live_issue159_full_native.py TF_DIR TT_ROOT")
    main(Path(sys.argv[1]),Path(sys.argv[2]))
