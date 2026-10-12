"""Issue #172 independent original TT residual source source parity."""
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
    "date_type":50,"german":42,"section_title":30,"quote_ref":22,
    "quote_type":22,"gap_exent":20,"ignore_note":15,"ed_page":14,
    "sup":14,"supplied_quantity":14,"supplied_unit":14,"sic":10,
    "surplus":10,"source_lang":5,"pb":4,"add_place":3,"pb_id":3,
    "sub":3,"gap_reasaon":2,"gap_reasonn":2,"hi":2,"surplus_reason":2,
    "cb":1,"del_rend":1,"figDesc":1,"figure":1,"pb_coptic_xml":1,
}
_TAG = re.compile(rb"<(/?)(norm|date_type|german|section_title|quote_ref|quote_type|"
    rb"gap_exent|ignore_note|ed_page|sup|supplied_quantity|supplied_unit|sic|"
    rb"surplus|source_lang|pb|add_place|pb_id|sub|gap_reasaon|gap_reasonn|"
    rb"hi|surplus_reason|cb|del_rend|figDesc|figure|pb_coptic_xml)\b([^<>]*)>")


def compare_original_residuals(source_records, native, *, expected_counts=None):
    """Independent original raw source kind/value/ordinal/word start+end."""
    if expected_counts is None:
        expected_counts = EXPECTED
    seen_records, observed = set(), set()
    counts = Counter()
    for rid, raw in source_records:
        if not rid or rid.casefold() in seen_records:
            raise ValueError("invalid/duplicated original TT residual source record")
        seen_records.add(rid.casefold())
        stacks = {kind: [] for kind in EXPECTED}
        closed_words, ordinal = 0, 0
        for m in _TAG.finditer(raw):
            closing, kind_bytes, attr_bytes = m.groups()
            kind = kind_bytes.decode("ascii")
            if kind == "norm":
                if closing:
                    closed_words += 1
                continue
            if not closing:
                ordinal += 1
                attr_key = b"rend" if kind == "hi" else kind_bytes
                parsed = re.fullmatch(
                    rb'\s+' + re.escape(attr_key) + rb'\s*=\s*"([^"]*)"\s*', attr_bytes
                )
                if parsed is None:
                    raise ValueError("original residual source missing/duplicate/unknown attribute")
                stacks[kind].append((
                    ordinal, unescape(parsed.group(1).decode("utf-8")), closed_words
                ))
                continue
            if not stacks[kind]:
                raise ValueError("original residual source closing without opening")
            original_ordinal, literal, start = stacks[kind].pop()
            key = (rid, original_ordinal)
            if key in observed:
                raise ValueError("original residual source duplicate source ordinal")
            observed.add(key)
            if native.get(key) != (kind, literal, start, closed_words):
                raise ValueError(f"original residual source native TF source mismatch at {key!r}")
            counts[kind] += 1
        if any(stacks.values()):
            raise ValueError("unclosed original TT residual source annotation")
    if observed != set(native):
        raise ValueError("original TT residual source event/native inventory mismatch")
    if dict(counts) != expected_counts:
        raise ValueError(f"residual source source tag inventory drift {dict(counts)}")
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
        "ed_lb_n":216, "ed_page_n":1047, "ed_pg_n":283,
        "chapter_n":3673, "marcion_chapter_n":403,"marcion_verse_n":10117,
        "petermann_chapter_n":248,"petermann_verse_n":2320,
        "hi_rend":5172,"note":2822,"gap_reason":1079,"supplied_reason":815,
        "note_note":333,"gap_unit":170,"supplied_source":99,
        "gap_quantity":94,"gap_extent":75,"supplied_evidence":67,
        "unclear_reason":64,"unclear":27,
        "gap":1162,"supplied":1865,"abbr":1620,
        "entity_head_tok":3677,"entity_text":3677,"entity_identity":901,
        "persName_type":245,"placeName_type":140,"placeName_ref":85,
        "roleName_type":80,"rs_type":18,"org_type":4,
        "pb_coptic_id":714,"p_n":386,"p":293,"p_source":157,
        "pb_n":74,"lb_nb":38,
        "verse":103,"verse_n_vid_n":96,"verse_n_vname":96,
        "v_id":63,"vid__n":6,"chapter_name":4,"ed_chapter_n":4,
        "chapter_2":3,"ch_n":2,"chapter":1,
    }.items():
        assert len(api.F.otype.s(kind)) == n,(kind,n)
    native,modes={},Counter()
    for kind,n_expected in EXPECTED.items():
        nodes=api.F.otype.s(kind)
        assert len(nodes)==n_expected,(kind,len(nodes),n_expected)
        for node in nodes:
            key=(api.F.source_record_id.v(node),api.F.source_ordinal.v(node))
            if not key[0] or not isinstance(key[1],int) or key in native:
                raise ValueError(f"duplicate original residual source source ordinal {key}")
            literal=api.F.value.v(node)
            assert isinstance(literal,str)
            mode=api.F.render_mode.v(node)
            assert mode in ("residual_span","residual_anchor"),(kind,mode)
            slots=api.E.oslots.s(node)
            assert len(slots)>=1,key
            if mode=="residual_anchor":
                assert len(slots)==1,key
            start,end=api.F.start_after_word_ordinal.v(node),api.F.end_after_word_ordinal.v(node)
            assert isinstance(start,int) and isinstance(end,int) and 0<=start<=end,key
            for word,char in (
                (api.F.start_word_ordinal.v(node),api.F.start_char.v(node)),
                (api.F.end_word_ordinal.v(node),api.F.end_char.v(node)),
            ):
                assert (word is None)==(char is None),key
            native[key]=(kind,literal,start,end)
            modes[(kind,mode)]+=1
    assert len(native)==308
    counts=compare_original_residuals(
        ((rid,raw) for rid,_path,raw,_pack in records(source_root)),
        native,
    )
    print(json.dumps({
        "result":"PASS independent source residual source/provenance native parity",
        "source_revision":PIN,"physical_records":2628,"canonical_slots":2394354,
        "source_nodes_by_kind":counts,"original_type_literal_ordinal_word_boundaries_exact":True,
        "modes":{"|".join(k):v for k,v in sorted(modes.items())},
    },sort_keys=True),flush=True)


if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("usage: python tests/live_issue172_full_native.py TF_DIR TT_ROOT")
    main(Path(sys.argv[1]),Path(sys.argv[2]))
