"""#173 independent original Horner English witness vs reloaded native TF."""
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
EXPECTED = {"trans_horner":385}
_TAG = re.compile(rb"<(/?)(norm|trans_horner|translation)\b([^<>]*)>")
_HORNER_ATTR = re.compile(rb'\s+trans_horner\s*=\s*"([^"]*)"\s*')


def compare_original_horner(source_records, native, *, expected_counts=None):
    """Original byte-scanned physical source, value, opening ID and word boundaries.

    Translation markup may cross Horner markup, so track original
    opening independently, without asserting an XML parent relationship.
    """
    if expected_counts is None:
        expected_counts = EXPECTED
    physical, seen = set(), set()
    counts = Counter()
    outside_translation = 0
    witness_files = Counter()
    word_ranges = []
    for rid, raw in source_records:
        if not rid or rid.casefold() in physical:
            raise ValueError("invalid or duplicate original Horner physical source record")
        physical.add(rid.casefold())
        norm_closed = 0
        translation_depth = 0
        original_ordinal = 0
        stack = []
        for m in _TAG.finditer(raw):
            closing, kind_b, attr_b = m.groups()
            kind = kind_b.decode("ascii")
            if kind == "norm":
                if closing:
                    norm_closed += 1
                continue
            if kind == "translation":
                translation_depth += -1 if closing else 1
                continue
            if not closing:
                original_ordinal += 1
                value = _HORNER_ATTR.fullmatch(attr_b)
                if value is None:
                    raise ValueError("original Horner missing/unknown/duplicate source attribute")
                if translation_depth <= 0:
                    outside_translation += 1
                stack.append((original_ordinal, unescape(value.group(1).decode("utf-8")), norm_closed))
                continue
            if not stack:
                raise ValueError("original Horner closing without opening")
            ordinal, literal, start = stack.pop()
            key = (rid, ordinal)
            if key in seen:
                raise ValueError("duplicated Horner original opening ordinal")
            seen.add(key)
            if native.get(key) != ("trans_horner", literal, start, norm_closed):
                raise ValueError(f"original Horner/native TF literal or boundary mismatch {key!r}")
            counts["trans_horner"] += 1
            witness_files[rid] += 1
            word_ranges.append(norm_closed - start)
        if stack:
            raise ValueError("unclosed original Horner source annotation")
    if seen != set(native):
        raise ValueError("original Horner/native TF source inventory mismatch")
    if dict(counts) != expected_counts:
        raise ValueError(f"original Horner corpus count drift {dict(counts)}")
    return {
        "source_counts":dict(counts),
        "physical_record_count":len(physical),
        "horner_annotated_records":dict(sorted(witness_files.items())),
        "outside_translation_at_opening":outside_translation,
        "min_norm_words":min(word_ranges) if word_ranges else None,
        "max_norm_words":max(word_ranges) if word_ranges else None,
    }


def main(tf_root:Path, source_root:Path):
    api=Fabric(locations=[str(tf_root)],silent="deep").load(
        "value render_mode source_record_id source_ordinal "
        "start_word_ordinal start_char start_after_word_ordinal "
        "end_word_ordinal end_char end_after_word_ordinal",silent="deep",
    )
    assert api and api.F.otype.maxSlot==2394354
    assert len(api.F.otype.s("document"))==2628
    for kind,n in {
        "lang":110148,"sbl_greek":1652,"sbl_apparatus":1095,
        "morph":78265,"multiword":35148,"ed_line_n":42189,
        "ed_lb_n":216,"ed_page_n":1047,"ed_pg_n":283,
        "chapter_n":3673,"marcion_chapter_n":403,"marcion_verse_n":10117,
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
        "date_type":50,"german":42,"section_title":30,"quote_ref":22,
        "quote_type":22,"gap_exent":20,"ignore_note":15,"ed_page":14,
        "sup":14,"supplied_quantity":14,"supplied_unit":14,"sic":10,
        "surplus":10,"source_lang":5,"pb":4,"add_place":3,"pb_id":3,
        "sub":3,"gap_reasaon":2,"gap_reasonn":2,"hi":2,"surplus_reason":2,
        "cb":1,"del_rend":1,"figDesc":1,"figure":1,"pb_coptic_xml":1,
    }.items():
        assert len(api.F.otype.s(kind))==n,(kind,n)
    native={}
    modes=Counter()
    for n in api.F.otype.s("trans_horner"):
        key=(api.F.source_record_id.v(n),api.F.source_ordinal.v(n))
        if not key[0] or not isinstance(key[1],int) or key in native:
            raise ValueError(f"duplicated Horner native source ordinal {key}")
        literal=api.F.value.v(n)
        assert isinstance(literal,str)
        mode=api.F.render_mode.v(n)
        assert mode in ("horner_span","horner_anchor"),(key,mode)
        slots=api.E.oslots.s(n)
        assert len(slots)>=1,key
        if mode=="horner_anchor":
            assert len(slots)==1,key
        start,end=api.F.start_after_word_ordinal.v(n),api.F.end_after_word_ordinal.v(n)
        assert isinstance(start,int) and isinstance(end,int) and 0<=start<=end,key
        for word,char in (
            (api.F.start_word_ordinal.v(n),api.F.start_char.v(n)),
            (api.F.end_word_ordinal.v(n),api.F.end_char.v(n)),
        ):
            assert (word is None)==(char is None),key
        native[key]=("trans_horner",literal,start,end)
        modes[mode]+=1
    assert len(native)==385
    parity=compare_original_horner(
        ((rid,raw) for rid,_path,raw,_pack in records(source_root)),
        native,
    )
    assert parity["outside_translation_at_opening"]==6, parity
    assert parity["min_norm_words"]==5,parity
    assert parity["max_norm_words"]==261,parity
    assert modes=={"horner_span":385},modes
    print(json.dumps({
        "result":"PASS native 385 original Horner English translation source parity",
        "upstream_commit":PIN,
        "word_slots":2394354,
        "modes":dict(modes),
        "exact_original_source_type_literal_ordinal_word_boundaries":True,
        **parity,
    },sort_keys=True),flush=True)


if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("usage: python tests/live_issue173_full_native.py TF_DIR TT_ROOT")
    main(Path(sys.argv[1]),Path(sys.argv[2]))
