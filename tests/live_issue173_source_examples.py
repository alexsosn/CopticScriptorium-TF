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

def main(root):
    total=0
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
        print(f"PASS source Horner witness {path}: {len(native)} distinct English source labels",flush=True)
    assert total==385
    print("PASS exact 385 English original Horner source labels in three pinned Pistis Sophia files",flush=True)

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python tests/live_issue173_source_examples.py TT_ROOT")
    main(sys.argv[1])
