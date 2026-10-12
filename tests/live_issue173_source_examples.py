"""Issue #173 pinned real original Horner source English witness samples."""
from collections import Counter
from pathlib import Path
import re
import sys
from copticscriptorium_tf.parser import parse_tt_record

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
FILES=(
    ("pistis-sophia/pistis.sophia_TT/pistis.sophia_book_1_part1.tt",162),
    ("pistis-sophia/pistis.sophia_TT/pistis.sophia_book_1_part2.tt",136),
    ("pistis-sophia/pistis.sophia_TT/pistis.sophia_book_1_part3.tt",87),
)



_TAGS=re.compile(rb"<(/?)(norm|translation|trans_horner)\b([^<>]*)>")


def independent_original_translation_word_ranges(raw):
    """Raw byte-tag scan; intentionally does not call the converter parser."""
    word=0
    opened={"translation":[],"trans_horner":[]}
    closed={"translation":[],"trans_horner":[]}
    for match in _TAGS.finditer(raw):
        closing,tag,_attrs=match.groups()
        kind=tag.decode("ascii")
        if kind=="norm":
            if closing:
                word+=1
            continue
        if not closing:
            opened[kind].append(word)
        else:
            assert opened[kind],(kind,"orphan source close")
            closed[kind].append((opened[kind].pop(),word))
    assert all(not v for v in opened.values())
    return closed

def main(root):
    total=0
    exact_matches=0
    contained_matches=0
    for path,expected in FILES:
        raw=(Path(root)/path).read_bytes()
        coll,folder,name=path.split("/")
        doc=parse_tt_record(
            raw,
            source_record_id=f"{coll}/{folder.removesuffix('_TT')}:{name.removesuffix('.tt')}",
            source_path=path,upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        native=doc.horner_annotations
        original=len(re.findall(rb"<trans_horner\s",raw))
        closed=len(re.findall(rb"</trans_horner>",raw))
        assert len(native)==original==closed==expected,(path,len(native),original,closed)
        assert [a.ordinal for a in native]==list(range(1,expected+1))
        assert len(doc.translations)>=expected,(path,len(doc.translations))
        assert all(a.word_ordinals for a in native),(path,"unexpected zero-word Horner")
        assert all(a.value for a in native),(path,"unexpected blank Horner")
        total+=len(native)
        ranges=independent_original_translation_word_ranges(raw)
        assert len(ranges["trans_horner"])==expected
        en=set(ranges["translation"])
        exact_matches+=sum(span in en for span in ranges["trans_horner"])
        contained_matches+=sum(
            any(t0<=h0 and h1<=t1 for t0,t1 in ranges["translation"])
            for h0,h1 in ranges["trans_horner"]
        )
        print(f"PASS source Horner witness {path}: {len(native)} distinct English source labels",flush=True)
    assert total==385
    assert exact_matches==376,(exact_matches,"original equal-range corpus drift")
    assert contained_matches==379,(contained_matches,"original contained-range corpus drift")
    print("PASS independently sourced 376/385 equal Horner-English spans; 6 not contained",flush=True)
    print("PASS exact 385 English original Horner source labels in three pinned Pistis Sophia files",flush=True)

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python tests/live_issue173_source_examples.py TT_ROOT")
    main(sys.argv[1])
