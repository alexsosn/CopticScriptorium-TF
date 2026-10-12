"""#162 real pinned original page/paragraph/witness source examples."""
from pathlib import Path
from collections import Counter
import re
import sys
from copticscriptorium_tf.parser import parse_tt_record

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS=("pb_coptic_id","p_n","p","p_source","pb_n","lb_nb")
FILES=(
    "pistis-sophia/pistis.sophia_TT/pistis.sophia_book_4_part3.tt",
    "besa-letters/besa.letters_TT/exhortations.tt",
    "AP/apophthegmata.patrum_TT/AP.177.ephrem.01.tt",
    "life-aphou/life.aphou_TT/life.aphou.02.tt",
    "magical-papyri/magical.papyri_TT/Pap.Copt.Mag.I_7.tt",
)


def main(root:Path):
    for rel in FILES:
        raw=(root/rel).read_bytes()
        corpus,dataset,file=rel.split("/")
        doc=parse_tt_record(
            raw,
            source_record_id=f"{corpus}/{dataset.removesuffix('_TT')}:{file.removesuffix('.tt')}",
            source_path=rel,upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        originals=Counter({
            k:len(re.findall(rb"<"+re.escape(k.encode("ascii"))+rb"\s",raw))
            for k in KINDS
        })
        actual=Counter(a.kind for a in doc.document_source_annotations)
        assert actual==+originals,(rel,originals,actual)
        assert [a.ordinal for a in doc.document_source_annotations]==list(
            range(1,len(doc.document_source_annotations)+1)
        )
        print(f"PASS original document marker sample {rel}: {dict(actual)}",flush=True)


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python tests/live_issue162_source_examples.py PINNED_TT")
    main(Path(sys.argv[1]))
