"""Pinned-source Mark 15:28 absent-verse proof against read-only Greek NT TF.

Checks original Coptic SBL occurrence identity, chapter/verse corroboration,
neighboring Greek parent verse nodes and the exact missing target. Emits
coordinates/counts only; neither original source passage nor verse text.
"""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tf.fabric import Fabric
from copticscriptorium_tf.nt_reference import (
    COPTIC_PIN, resolve_coptic_sbl_references, morphgnt_verse_is_absent,
)
from copticscriptorium_tf.nt_modules import (
    GREEK_PARENT_PIN, validate_greek_release,
)
from copticscriptorium_tf.parser import parse_tt_record

MARK15_SOURCE = "sahidica.mark/sahidica.mark_TT/Mark_15.tt"
MARK15_RECORD = "sahidica.mark/sahidica.mark:Mark_15"


def check_repo(root: Path, pin: str) -> None:
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args],
                              check=True, capture_output=True, text=True).stdout.strip()
    if git("rev-parse", "HEAD") != pin or git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("source or Greek parent revision not exact and clean")


def verify(coptic_root: Path, greek_root: Path) -> dict:
    check_repo(coptic_root, COPTIC_PIN)
    check_repo(greek_root, GREEK_PARENT_PIN)
    raw = (coptic_root / MARK15_SOURCE).read_bytes()
    document = parse_tt_record(
        raw, source_record_id=MARK15_RECORD, source_path=MARK15_SOURCE,
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=COPTIC_PIN,
    )
    if document.metadata.get("book") != "Mark" or document.metadata.get("chapter") != "15":
        raise ValueError("unexpected Mark 15 TT source metadata")
    if len(document.sbl_annotations) != 78:
        raise ValueError("unexpected pinned Mark 15 source annotation inventory")
    greek_dir = greek_root / "tf" / "2022"
    api = Fabric(locations=[str(greek_dir)], silent="deep").load(
        "book chapter verse", silent="deep"
    )
    if not api:
        raise ValueError("pinned Greek NT parent failed to load")
    validate_greek_release(greek_dir, api)

    def lookup(book, chapter, verse):
        try:
            return api.T.nodeFromSection((book, chapter, verse))
        except (KeyError, ValueError):
            return None

    neighbors = {}
    for verse in (27, 28, 29):
        node = lookup("Mark", 15, verse)
        if verse == 28:
            if node is not None or not morphgnt_verse_is_absent("Mark", 15, 28):
                raise ValueError("wrong pinned Greek Mark 15:28 edition-absence proof")
        else:
            if node is None or api.F.otype.v(node) != "verse":
                raise ValueError("neighboring Greek verse missing")
            if api.T.sectionFromNode(node) != ("Mark", 15, verse):
                raise ValueError("neighboring Greek verse lookup mismatched")
        neighbors[verse] = node is not None

    refs = resolve_coptic_sbl_references(document, lookup=lookup)
    if len(refs) != len(document.sbl_annotations):
        raise ValueError("original Mark 15 source SBL annotation loss")
    item = refs[42]
    original = document.sbl_annotations[42]
    if (
        original.kind != "sbl_greek"
        or original.ordinal != 43
        or item.source_record_id != MARK15_RECORD
        or item.source_verse_n != "28"
        or item.source_verse_vid != "41N 15:28"
        or not item.source_word_ordinals
        or item.status != "edition_unavailable"
        or item.target_book != "Mark"
        or item.target_chapter != 15
        or item.target_verse != 28
        or item.target_node is not None
        or item.shared_id is not None
    ):
        raise ValueError("Mark15:28 original SBL occurrence provenance/absence changed")
    for verse in (27, 29):
        matches = [r for r in refs if r.source_verse_n == str(verse)
                   and r.source_kind == "sbl_greek"]
        if len(matches) != 1 or matches[0].status != "reference_candidate":
            raise ValueError("source-backed neighboring Mark 15 verse must remain candidate")
    result = {
        "status": "pass",
        "source": MARK15_RECORD,
        "source_annotation_ordinal": 43,
        "source_annotation_kind": "sbl_greek",
        "coptic_book": "Mark",
        "coptic_chapter": 15,
        "coptic_verse": 28,
        "classification": item.status,
        "target_node": None,
        "target_ref": None,
        "greek_neighbor_verse_presence": {
            "15:27": neighbors[27],
            "15:28": neighbors[28],
            "15:29": neighbors[29],
        },
        "source_commit": COPTIC_PIN,
        "greek_parent_commit": GREEK_PARENT_PIN,
    }
    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: live_issue126_mark15.py PINNED_COPTIC PINNED_GREEK")
    print(json.dumps(verify(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))
