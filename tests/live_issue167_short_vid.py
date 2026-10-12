"""Pinned 1 Corinthians 1:9 shortened CTS field: two real physical witnesses.

This source-only proof checks exact original TT Git blobs, whole-word source
markers and independently pinned Greek NT verse-parent reverse sections.
It emits source record IDs, counts and addresses only, no corpus text.
"""
from collections import Counter
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.nt_reference import (
    COPTIC_PIN, PINNED_1COR1_SHORT_VID_BLOB,
    PINNED_1COR1_SHORT_VID_RECORDS,
    resolve_coptic_sbl_references,
)
from copticscriptorium_tf.nt_modules import GREEK_PARENT_PIN, validate_greek_release

ORIGINALS = (
    ("sahidica.1corinthians/sahidica.1corinthians:1Cor_01",
     "sahidica.1corinthians/sahidica.1corinthians_TT/1Cor_01.tt"),
    ("coptic-treebank/coptic.treebank:1Cor_01",
     "coptic-treebank/coptic.treebank_TT/1Cor_01.tt"),
)


def verify_repo(root: Path, expected: str):
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args],
                              check=True, capture_output=True, text=True).stdout.strip()
    if git("rev-parse", "HEAD") != expected or git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("original source/Greek parent revision is not exact and clean")
    return git


def verify(coptic_root: Path, greek_root: Path) -> dict:
    git = verify_repo(coptic_root, COPTIC_PIN)
    verify_repo(greek_root, GREEK_PARENT_PIN)
    tf_dir = greek_root/"tf"/"2022"
    api = Fabric(locations=[str(tf_dir)], silent="deep").load("book chapter verse", silent="deep")
    if not api:
        raise ValueError("Greek NT parent TF unavailable")
    validate_greek_release(tf_dir, api)

    def lookup(book, chapter, verse):
        try:
            node=api.T.nodeFromSection((book,chapter,verse))
        except (KeyError,ValueError):
            return None
        if node is not None:
            if api.F.otype.v(node) != "verse" or api.T.sectionFromNode(node) != (book,chapter,verse):
                raise ValueError("Greek NT section or target node identity mismatch")
        return node

    greek_nine = lookup("1_Corinthians", 1, 9)
    if greek_nine is None:
        raise ValueError("1 Corinthians 1:9 absent from the independent pinned Greek verse parent")

    physicals = {}
    recovered=[]
    for record,path in ORIGINALS:
        if record not in PINNED_1COR1_SHORT_VID_RECORDS:
            raise ValueError("unreviewed original source identity")
        if git("hash-object", path) != PINNED_1COR1_SHORT_VID_BLOB:
            raise ValueError("pinned original TT file Git blob changed")
        document = parse_tt_record((coptic_root/path).read_bytes(),
            source_record_id=record, source_path=path,
            upstream_repository="CopticScriptorium/corpora",upstream_commit=COPTIC_PIN)
        if (document.metadata.get("chapter") != "1"
            or document.metadata.get("book") != "1Cor"
            or document.metadata.get("document_cts_urn")
                != "urn:cts:copticLit:nt.1cor.sahidica_ed:1"):
            raise ValueError("original 1 Corinthians 1 CTS/document identity drift")
        refs = resolve_coptic_sbl_references(document, lookup=lookup)
        if len(refs) != len(document.sbl_annotations):
            raise ValueError("source SBL occurrence lost")
        if Counter(a.kind for a in document.sbl_annotations) != {
            "sbl_greek": 31, "sbl_apparatus": 12,
        }:
            raise ValueError("source SBL kind inventory changed")
        ann=document.sbl_annotations[11]
        source=refs[11]
        if (
            ann.ordinal != 12 or ann.kind != "sbl_greek"
            or source.source_ordinal != 12 or source.source_record_id != record
            or source.source_kind != "sbl_greek"
            or source.source_verse_n != "9"
            or source.source_vid_n != ".9"
            or source.source_verse_vid != "46N 1:9"
            or source.source_word_ordinals != ann.word_ordinals
            or not ann.word_ordinals
            or source.status != "reference_candidate"
            or source.target_book != "1_Corinthians"
            or source.target_chapter != 1 or source.target_verse != 9
            or source.target_node != greek_nine
            or source.shared_id is None
            or "gitblob-verified-short-vid_n" not in source.evidence
        ):
            raise ValueError("original 1Cor1:9 source/Greek target two-marker proof failed")
        if [r.source_ordinal for r in refs if "gitblob-verified-short-vid_n" in r.evidence] != [12]:
            raise ValueError("unreviewed short CTS marker promoted a source annotation")
        if any(r.status != "reference_candidate"
               and (r.target_node is not None or r.shared_id is not None)
               for r in refs):
            raise ValueError("noncandidate contains fabricated Greek target")
        physicals[record]=dict(sorted(Counter(r.status for r in refs).items()))
        recovered.append((record,source.shared_id))
    if len(recovered) != 2 or recovered[0][1] != recovered[1][1]:
        raise ValueError("treebank/canonical physical source identity or target drift")
    return {
        "status": "pass",
        "scope": "Original pinned Coptic SBL verse-address evidence; no Greek lexical/token equivalence",
        "coptic_pin": COPTIC_PIN, "greek_parent_pin": GREEK_PARENT_PIN,
        "original_tt_git_blob": PINNED_1COR1_SHORT_VID_BLOB,
        "source_verse_address": "1_Corinthians:1:9",
        "source_sbl_ordinal": 12,
        "physical_witnesses": physicals,
        "new_candidate_physical_occurrences": len(recovered),
        "greek_parent_verse_node_count": 1,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: live_issue167_short_vid.py PINNED_COPTIC PINNED_GREEK")
    print(json.dumps(verify(Path(sys.argv[1]),Path(sys.argv[2])),sort_keys=True))
