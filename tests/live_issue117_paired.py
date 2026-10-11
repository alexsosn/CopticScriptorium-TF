"""Source-only pinned 1Cor14 pair-evidence audit, no text output or corpus copies."""
from collections import Counter
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.nt_reference import COPTIC_PIN, resolve_coptic_sbl_references
from copticscriptorium_tf.nt_modules import GREEK_PARENT_PIN, validate_greek_release
from copticscriptorium_tf.nt_paired_verse import paired_word_verses, source_pair_for_sbl

REC = "sahidica.1corinthians/sahidica.1corinthians:1Cor_14"
PATH = "sahidica.1corinthians/sahidica.1corinthians_TT/1Cor_14.tt"


def verify(root: Path, parent: Path) -> dict:
    for repo, pin in ((root, COPTIC_PIN), (parent, GREEK_PARENT_PIN)):
        def git(*args):
            return subprocess.run(["git","-C",str(repo),*args],
                                  check=True,capture_output=True,text=True).stdout.strip()
        if git("rev-parse","HEAD") != pin or git("status","--porcelain","--untracked-files=all"):
            raise ValueError("source or Greek NT checkout not pinned and clean")
    doc = parse_tt_record((root/PATH).read_bytes(),source_record_id=REC,
        source_path=PATH,upstream_repository="CopticScriptorium/corpora",
        upstream_commit=COPTIC_PIN)
    original = Counter(a.kind for a in doc.sbl_annotations)
    if original != {"sbl_greek":40,"sbl_apparatus":21}:
        raise ValueError("unexpected 1Cor14 physical source annotation count")
    greek_root = parent/"tf"/"2022"
    api = Fabric(locations=[str(greek_root)],silent="deep").load("book chapter verse",silent="deep")
    if not api:
        raise ValueError("pinned Greek NT unavailable")
    validate_greek_release(greek_root,api)

    def lookup(book,ch,ve):
        try:
            node=api.T.nodeFromSection((book,ch,ve))
        except (KeyError,ValueError):
            return None
        if node is not None:
            if api.F.otype.v(node)!="verse" or api.T.sectionFromNode(node)!=(book,ch,ve):
                raise ValueError("Greek verse parent mismatch")
        return node

    pairs=paired_word_verses(doc)
    refs=resolve_coptic_sbl_references(doc,lookup=lookup)
    if len(refs)!=len(doc.sbl_annotations) or len(pairs)!=len(doc.words):
        raise ValueError("source SBL or native Coptic word conservation failed")
    by_kind=Counter((r.source_kind,r.status) for r in refs)
    statuses=Counter(r.status for r in refs)
    distinct=sorted(set(r.target_verse for r in refs if r.status=="reference_candidate"))
    if statuses != {"reference_candidate": 61} or by_kind != {
        ("sbl_greek", "reference_candidate"): 40,
        ("sbl_apparatus", "reference_candidate"): 21,
    } or distinct != list(range(1, 41)):
        raise ValueError("real paired TT source coverage is not 61 occurrences / 40 verses")
    for r,a in zip(refs,doc.sbl_annotations,strict=True):
        if (r.source_record_id,r.source_ordinal,r.source_kind)!=(REC,a.ordinal,a.kind):
            raise ValueError("original Coptic SBL kind/ordinal mismatch")
        if r.status=="reference_candidate":
            pair=source_pair_for_sbl(doc,pairs,a.word_ordinals)
            if (pair is None or pair.number != r.target_verse or r.target_chapter!=14
                or r.source_verse_n is not None or r.source_verse_vid != pair.editor
                or r.target_node is None or r.shared_id is None):
                raise ValueError("paired source evidence or Greek parent candidate invalid")
        elif r.target_node is not None or r.shared_id is not None:
            raise ValueError("incomplete Coptic source got fabricated Greek reference")
    return {"status":"pass","source":REC,"original_annotations":len(refs),
            "word_slots":len(doc.words),
            "candidate_verse_numbers":distinct,
            "distinct_target_verses":len(distinct),
            "by_kind_status":{f"{k}:{v}":c for (k,v),c in sorted(by_kind.items())},
            "statuses":dict(sorted(statuses.items())),
            "source_pin":COPTIC_PIN,"greek_parent_pin":GREEK_PARENT_PIN,
            "scope":"Original Coptic whole-word paired verse/editor labels, NOT Greek lexical alignment"}


if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("usage: python tests/live_issue117_paired.py PINNED_TT PINNED_GREEK")
    print(json.dumps(verify(Path(sys.argv[1]),Path(sys.argv[2])),sort_keys=True))
