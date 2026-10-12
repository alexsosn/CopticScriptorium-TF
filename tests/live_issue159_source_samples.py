"""#159 real pinned source sample evidence, independent raw opening census."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

from copticscriptorium_tf.parser import parse_tt_record

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS=("entity_head_tok","entity_text","entity_identity","persName_type",
       "placeName_type","placeName_ref","roleName_type","rs_type","org_type")
FILES=(
    "proclus-homilies/proclus.homilies_TT/proclus.23.nativity.tt",
    "life-aphou/life.aphou_TT/life.aphou.01.tt",
    "abraham/shenoute.abraham_TT/YA525-530.tt",
)


def main(root: Path):
    for rel in FILES:
        raw=(root/rel).read_bytes()
        corpus,dataset,file=rel.split("/")
        doc=parse_tt_record(
            raw,source_record_id=f"{corpus}/{dataset.removesuffix('_TT')}:{file.removesuffix('.tt')}",
            source_path=rel,upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        source=Counter({
            kind:len(re.findall(rb"<"+re.escape(kind.encode("ascii"))+rb"\s",raw))
            for kind in KINDS
        })
        native=Counter(a.kind for a in doc.entity_source_annotations)
        assert native==+source,(rel,source,native)
        assert [a.ordinal for a in doc.entity_source_annotations]==list(
            range(1,len(doc.entity_source_annotations)+1)
        )
        print(f"PASS entity/name source witness {rel}: {dict(native)}",flush=True)


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python tests/live_issue159_source_samples.py TT_ROOT")
    main(Path(sys.argv[1]))
