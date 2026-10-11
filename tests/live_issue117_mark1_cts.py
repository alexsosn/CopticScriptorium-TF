"""Original pinned Mark1 CTS dual-label address candidates, no corpus text output.

Analyzes both PHYSICAL Coptic TT witnesses against an independent exact
Greek NT TF parent. Does not assume their complete source bytes match.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tf.fabric import Fabric

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.nt_reference import (
    COPTIC_PIN, CTS_VERSE, VERSE_LABEL, resolve_coptic_sbl_references,
)
from copticscriptorium_tf.nt_modules import GREEK_PARENT_PIN, validate_greek_release

SOURCES = (
    ("sahidica.mark/sahidica.mark:Mark_01",
     "sahidica.mark/sahidica.mark_TT/Mark_01.tt"),
    ("coptic-treebank/coptic.treebank:Mark_01",
     "coptic-treebank/coptic.treebank_TT/Mark_01.tt"),
)


def check_repo(root: Path, pin: str) -> None:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    if git("rev-parse", "HEAD") != pin or git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("not a clean exact pinned source corpus checkout")


def audit(source: Path, greek_parent: Path) -> dict:
    check_repo(source, COPTIC_PIN)
    check_repo(greek_parent, GREEK_PARENT_PIN)
    greek_tf = greek_parent / "tf" / "2022"
    api = Fabric(locations=[str(greek_tf)], silent="deep").load("book chapter verse", silent="deep")
    if not api:
        raise ValueError("Greek NT parent not loaded")
    validate_greek_release(greek_tf, api)

    def lookup(book, chapter, verse):
        try:
            node = api.T.nodeFromSection((book, chapter, verse))
        except (KeyError, ValueError):
            return None
        if node is not None:
            if api.F.otype.v(node) != "verse" or api.T.sectionFromNode(node) != (book, chapter, verse):
                raise ValueError("forged non-verse or wrong Greek parent section")
        return node

    witnesses = {}
    identities = []
    for record, path in SOURCES:
        raw = (source / path).read_bytes()
        original_git_blob = subprocess.run(
            ["git", "-C", str(source), "hash-object", path],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        document = parse_tt_record(
            raw, source_record_id=record, source_path=path,
            upstream_repository="CopticScriptorium/corpora", upstream_commit=COPTIC_PIN,
        )
        source_kinds = Counter(a.kind for a in document.sbl_annotations)
        if source_kinds != {"sbl_greek": 45, "sbl_apparatus": 36}:
            raise ValueError("original Mark1 annotation counts changed")
        refs = resolve_coptic_sbl_references(document, lookup=lookup)
        if len(refs) != 81:
            raise ValueError("original Mark1 source occurrence loss")
        statuses = Counter(r.status for r in refs)
        by_kind_status = Counter((r.source_kind, r.status) for r in refs)
        accepted = []
        for ann, r in zip(document.sbl_annotations, refs, strict=True):
            if (r.source_record_id, r.source_ordinal, r.source_kind) != (
                record, ann.ordinal, ann.kind
            ):
                raise ValueError("original SBL source identity/ordinal drift")
            if r.status != "reference_candidate":
                if r.target_node is not None or r.shared_id is not None:
                    raise ValueError("noncandidate contains foreign Greek target")
                continue
            vid = CTS_VERSE.fullmatch(r.source_vid_n or "")
            if (
                r.source_verse_vid is not None
                or not vid
                or vid.group(1) != "mark"
                or int(vid.group(2)) != 1
                or r.source_verse_n is None
                or not r.source_verse_n.isdecimal()
                or int(vid.group(3)) != int(r.source_verse_n)
                or r.target_chapter != 1 or r.target_book != "Mark"
                or r.target_verse != int(r.source_verse_n)
                or not r.source_word_ordinals
                or (r.source_kind == "sbl_greek"
                    and VERSE_LABEL.fullmatch(ann.value or ""))
                or r.target_node is None
                or r.shared_id is None
                or api.T.sectionFromNode(r.target_node) != ("Mark", 1, r.target_verse)
            ):
                raise ValueError("Mark1 candidate does not have two exact original marker proofs")
            accepted.append((r.source_ordinal, r.source_kind, r.target_verse))
        if not (statuses.get("reference_candidate", 0) > 0
                and statuses.get("ambiguous", 0) > 0):
            raise ValueError("Mark1 dual-marker pilot did not preserve both accepted and rejected cases")
        identities.append((original_git_blob, tuple(accepted), statuses))
        witnesses[record] = {
            "status_counts": dict(sorted(statuses.items())),
            "by_kind_status": {
                f"{k}:{v}": count for (k, v), count in sorted(by_kind_status.items())
            },
            "original_annotations": 81,
            "accepted_unique_target_verses": len(set(v for _, _, v in accepted)),
            "accepted_source_ordinals": [ordinal for ordinal, _, _ in accepted],
            "git_blob": original_git_blob,
        }

    # These are two different full TT source files but identical attested SBL
    # source markers; do not collapse them into one physical source record.
    if identities[0][0] == identities[1][0]:
        raise ValueError("unexpected identical canonical/treebank Mark1 source blobs")
    if identities[0][1:] != identities[1][1:]:
        raise ValueError("canonical and treebank Mark1 annotation candidate parity drift")
    return {
        "status": "pass", "source_commit": COPTIC_PIN,
        "greek_parent_commit": GREEK_PARENT_PIN,
        "scope": "Only original Coptic verse_n+CTS vid_n, no Greek lexical/text alignment",
        "physical_witnesses": witnesses,
        "total_candidate_occurrences": sum(
            w["status_counts"].get("reference_candidate", 0) for w in witnesses.values()
        ),
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue117_mark1_cts.py PINNED_COPTIC PINNED_GREEK")
    print(json.dumps(audit(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))
