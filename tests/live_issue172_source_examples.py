"""Issue #172 real pinned original TT residual source annotation samples."""
from collections import Counter
from pathlib import Path
import re
import sys
from copticscriptorium_tf.parser import parse_tt_record

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS=(
    "date_type","german","section_title","quote_ref","quote_type",
    "gap_exent","ignore_note","ed_page","sup","supplied_quantity",
    "supplied_unit","sic","surplus","source_lang","pb","add_place",
    "pb_id","sub","gap_reasaon","gap_reasonn","hi","surplus_reason",
    "cb","del_rend","figDesc","figure","pb_coptic_xml",
)
FILES=(
    "life-aphou/life.aphou_TT/life.aphou.01.tt",
    "besa-letters/besa.letters_TT/on_vigilance.tt",
    "bohairic-life-shenoute/bohairic.life.shenoute_TT/bohairic.life.shenoute_01.tt",
    "shenoute-a22/shenoute.a22_TT/a22.YB307-320.tt",
    "doc-papyri/doc.papyri_TT/cpr.2.237.tt",
)


def main(root):
    for rel in FILES:
        raw=(Path(root)/rel).read_bytes()
        coll,folder,filename=rel.split("/")
        doc=parse_tt_record(
            raw,
            source_record_id=f"{coll}/{folder.removesuffix('_TT')}:{filename.removesuffix('.tt')}",
            source_path=rel,upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        counts=Counter({
            k:len(re.findall(rb"<"+re.escape(k.encode())+rb"\s",raw))
            for k in KINDS
        })
        actual=Counter(a.kind for a in doc.residual_annotations)
        assert actual==+counts,(rel,counts,actual)
        assert [a.ordinal for a in doc.residual_annotations]==list(
            range(1,len(doc.residual_annotations)+1)
        )
        print(f"PASS residual original TT witness {rel}: {dict(actual)}",flush=True)


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python tests/live_issue172_source_examples.py TT_ROOT")
    main(sys.argv[1])
