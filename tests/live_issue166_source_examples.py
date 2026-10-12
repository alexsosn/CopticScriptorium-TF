"""Issue #166 actual TT witnesses, sampled before full native conversion."""
from collections import Counter
from pathlib import Path
import re
import sys
from copticscriptorium_tf.parser import parse_tt_record

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS=("verse","verse_n_vid_n","verse_n_vname","v_id","vid__n",
       "chapter_name","ed_chapter_n","chapter_2","ch_n","chapter")
FILES=(
    "sahidica.1corinthians/sahidica.1corinthians_TT/1Cor_14.tt",
    "coptic-treebank/coptic.treebank_TT/Jonah_01.tt",
    "abraham/shenoute.abraham_TT/YA535-540.tt",
    "AP/apophthegmata.patrum_TT/AP.025.isaac-cells.12.tt",
    "coptic-treebank/coptic.treebank_TT/1Cor_01.tt",
    "bohairic-lausiac/bohairic.lausiac_TT/bohairic.lausiac_01.tt",
)


def main(root):
    for rel in FILES:
        raw=(Path(root)/rel).read_bytes()
        coll,folder,name=rel.split("/")
        doc=parse_tt_record(
            raw,source_record_id=f"{coll}/{folder.removesuffix('_TT')}:{name.removesuffix('.tt')}",
            source_path=rel,upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        source=Counter({k:len(re.findall(rb"<"+re.escape(k.encode())+rb"\s",raw)) for k in KINDS})
        actual=Counter(a.kind for a in doc.alternate_reference_annotations)
        assert actual==+source,(rel,source,actual)
        assert [a.ordinal for a in doc.alternate_reference_annotations]==list(
            range(1,len(doc.alternate_reference_annotations)+1)
        )
        print(f"PASS pinned alternate source ref witness {rel}: {dict(actual)}",flush=True)


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python tests/live_issue166_source_examples.py TT_ROOT")
    main(sys.argv[1])
