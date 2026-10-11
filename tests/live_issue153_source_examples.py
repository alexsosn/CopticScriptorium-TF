"""#153 independent real-source sample count against source annotation parser."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

from copticscriptorium_tf.parser import parse_tt_record

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS = (
    "hi_rend","note","gap_reason","supplied_reason","note_note","gap_unit",
    "supplied_source","gap_quantity","gap_extent","supplied_evidence",
    "unclear_reason","unclear",
)
FILES = (
    "AP/apophthegmata.patrum_TT/AP.001.n135.mother.tt",
    "johannes-canons/johannes.canons_TT/johannes.canons.FA191-192.tt",
    "life-paul-tamma/life.paul.tamma_TT/life.paul.tamma.01.tt",
    "pistis-sophia/pistis.sophia_TT/pistis.sophia_Postscript_part1.tt",
)


def main(root: Path) -> None:
    for rel in FILES:
        raw = (root/rel).read_bytes()
        corpus, dataset_dir, filename = rel.split("/")
        doc = parse_tt_record(
            raw, source_record_id=f"{corpus}/{dataset_dir.removesuffix('_TT')}:{filename.removesuffix('.tt')}",
            source_path=rel, upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        opening = Counter({
            k: len(re.findall(rb"<" + re.escape(k.encode("ascii")) + rb"\s", raw))
            for k in KINDS
        })
        observed = Counter(a.kind for a in doc.editorial_annotations)
        assert observed == +opening, (rel,opening,observed)
        assert [a.ordinal for a in doc.editorial_annotations] == list(
            range(1,len(doc.editorial_annotations)+1)
        )
        print(f"PASS original editorial TT source sample {rel}: {dict(observed)}",flush=True)


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python tests/live_issue153_source_examples.py PINNED_TT")
    main(Path(sys.argv[1]))
