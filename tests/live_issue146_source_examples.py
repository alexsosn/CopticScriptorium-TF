"""#146 independent raw TT vs parsed source sample counts, no corpus export."""
from __future__ import annotations

from pathlib import Path
import re
import sys
from collections import Counter

from copticscriptorium_tf.parser import parse_tt_record

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS=("chapter_n","marcion_chapter_n","marcion_verse_n",
       "petermann_chapter_n","petermann_verse_n")
FILES=(
    "pistis-sophia/pistis.sophia_TT/pistis.sophia_Postscript_part1.tt",
    "AP/apophthegmata.patrum_TT/AP.001.n135.mother.tt",
    "bohairic-lausiac/bohairic.lausiac_TT/bohairic.lausiac_01.tt",
)


def main(root: Path):
    for rel in FILES:
        raw=(root/rel).read_bytes()
        corpus,dataset_dir,file=rel.split("/")
        doc=parse_tt_record(
            raw,source_record_id=f"{corpus}/{dataset_dir.removesuffix('_TT')}:{file.removesuffix('.tt')}",
            source_path=rel,upstream_repository="CopticScriptorium/corpora",upstream_commit=PIN,
        )
        opens = Counter({k:len(re.findall(rb"<"+re.escape(k.encode())+rb"\s",raw)) for k in KINDS})
        observed=Counter(x.kind for x in doc.reference_annotations)
        assert observed==+opens, (rel,observed,opens)
        assert [x.ordinal for x in doc.reference_annotations]==list(range(1,len(doc.reference_annotations)+1))
        print(f"PASS reference TT sample event parity {rel}: {dict(observed)}",flush=True)


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python tests/live_issue146_source_examples.py PINNED_TT")
    main(Path(sys.argv[1]))
