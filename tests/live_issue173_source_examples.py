"""#173 pinned actual three 1MB original Horner-English TT translation samples."""
from collections import Counter
from pathlib import Path
import re
import sys
from copticscriptorium_tf.parser import parse_tt_record

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
SAMPLES=(("pistis.sophia_book_1_part1.tt",162),
         ("pistis.sophia_book_1_part2.tt",136),
         ("pistis.sophia_book_1_part3.tt",87))


def main(source_root:Path):
    total=0
    for file_name,expected in SAMPLES:
        rel="pistis-sophia/pistis.sophia_TT/"+file_name
        raw=(source_root/rel).read_bytes()
        native=parse_tt_record(
            raw,
            source_record_id=f"pistis-sophia/pistis.sophia:{file_name.removesuffix('.tt')}",
            source_path=rel,upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        original_opens=len(re.findall(rb"<trans_horner\s",raw))
        original_closes=raw.count(b"</trans_horner>")
        assert original_opens==original_closes==expected,(rel,original_opens,original_closes)
        attrs=native.horner_translation_annotations
        assert len(attrs)==expected,(rel,len(attrs),expected)
        assert [a.ordinal for a in attrs]==list(range(1,expected+1))
        assert attrs[0].value and native.translations,rel
        assert attrs[0].value!=native.translations[0].text,rel
        print(f"PASS pinned Horner source witness {rel}: {expected} distinct English tags",flush=True)
        total+=expected
    assert total==385,total


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python tests/live_issue173_source_examples.py TT_ROOT")
    main(Path(sys.argv[1]))
