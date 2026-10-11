"""#156 source-backed examples including Sahidic OT abbreviation ZIP member."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.sbl_source_census import records

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
FILES = (
    "johannes-canons/johannes.canons_TT/johannes.canons.FA191-192.tt",
    "life-paul-tamma/life.paul.tamma_TT/life.paul.tamma.01.tt",
)


def check(raw, rid, path):
    doc = parse_tt_record(
        raw, source_record_id=rid, source_path=path,
        upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN,
    )
    expected = Counter({
        kind: len(re.findall(rb"<" + kind.encode() + rb"\s", raw))
        for kind in ("gap","supplied","abbr")
    })
    actual = Counter(x.kind for x in doc.intervention_annotations)
    assert actual == +expected, (rid,actual,expected)
    assert [x.ordinal for x in doc.intervention_annotations] == list(
        range(1,len(doc.intervention_annotations)+1)
    )
    print(f"PASS original gap/supplied/abbr source sample {rid}: {dict(actual)}",flush=True)
    return expected


def main(root: Path):
    for rel in FILES:
        corpus, source_dir, file = rel.split("/")
        rid = f"{corpus}/{source_dir.removesuffix('_TT')}:{file.removesuffix('.tt')}"
        check((root/rel).read_bytes(), rid, rel)
    matched = 0
    for rid, path, raw, _pack in records(root):
        if "sahidic.ot" in rid and re.search(rb"<abbr\s",raw):
            counts=check(raw,rid,path)
            assert counts["abbr"] > 0
            matched += 1
            break
    assert matched == 1, "no pinned original OT abbreviation ZIP member found"


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python tests/live_issue156_source_examples.py PINNED_TT")
    main(Path(sys.argv[1]))
