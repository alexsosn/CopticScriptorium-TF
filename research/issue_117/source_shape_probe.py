"""Independent pinned TT attribute-shape census (no source text emitted).

This raw scanner intentionally does NOT invoke the TT parser, Coptic resolver,
or the new diagnosis collector. It verifies that the categories correspond
to actual public pinned source records, and treats treebank copies as separate
physical sources even if their TT payload is byte-identical.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
TAG = re.compile(rb'<(sbl_greek|sbl_apparatus|verse_n|verse_vid|vid_n)\s+[^>]*?>')
VALUE = re.compile(rb'^<([a-z_]+)\s+\1="([^"]*)"')
EDITOR = re.compile(rb"^(?:41N|46N) [1-9][0-9]*:[1-9][0-9]*$")
CTS = re.compile(rb"^urn:cts:copticLit:nt\.[a-z0-9]+\.sahidica_ed:[1-9][0-9]*\.[1-9][0-9]*$")

SOURCES = {
    "sahidica.mark/sahidica.mark_TT/Mark_01.tt": {
        "sbl_greek": 45, "sbl_apparatus": 36, "verse_n": 45,
        "verse_vid": 0, "vid_n": 45,
        "vid_n.cts_verse": 41, "vid_n.editor_reference": 1,
        "vid_n.other": 3, "sbl_greek.editor_reference": 10,
    },
    "coptic-treebank/coptic.treebank_TT/Mark_01.tt": {
        "sbl_greek": 45, "sbl_apparatus": 36, "verse_n": 45,
        "verse_vid": 0, "vid_n": 45,
        "vid_n.cts_verse": 41, "vid_n.editor_reference": 1,
        "vid_n.other": 3, "sbl_greek.editor_reference": 10,
    },
    "sahidica.1corinthians/sahidica.1corinthians_TT/1Cor_01.tt": {
        "sbl_greek": 31, "sbl_apparatus": 12, "verse_n": 31,
        "verse_vid": 31, "vid_n": 31,
        "vid_n.cts_verse": 30, "vid_n.other": 1,
    },
}


def audit(root: Path) -> dict:
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    if commit != PIN:
        raise ValueError("incorrect pinned Coptic TT source commit")
    observations = {}
    hashes = {}
    for source, expected in SOURCES.items():
        raw = (root / source).read_bytes()
        hashes[source] = hashlib.sha256(raw).hexdigest()
        found = Counter()
        for match in TAG.finditer(raw):
            key = match.group(1).decode("ascii")
            found[key] += 1
            value_match = VALUE.match(match.group(0))
            if not value_match or value_match.group(1).decode("ascii") != key:
                raise ValueError("malformed pinned TT attribute opening tag")
            value = value_match.group(2)
            if key == "vid_n":
                category = ("cts_verse" if CTS.fullmatch(value) else
                            "editor_reference" if EDITOR.fullmatch(value) else "other")
                found[f"vid_n.{category}"] += 1
            if key == "sbl_greek" and EDITOR.fullmatch(value):
                found["sbl_greek.editor_reference"] += 1
        if dict(found) != expected:
            raise ValueError(f"pinned TT source attribute-shape drift: {source}")
        observations[source] = dict(sorted(found.items()))
    paths = list(SOURCES)
    if hashes[paths[0]] != hashes[paths[1]]:
        raise ValueError("Mark1 canonical and treebank TT bytes are no longer identical")
    return {
        "status": "pass", "upstream_commit": PIN,
        "physical_documents_examined": len(SOURCES),
        "treebank_mark1_exact_byte_duplicate": True,
        "source_shape_counts": observations,
        "scope": "Untrusted original XML-like label shapes; no source contents, normalization or cross-corpus mapping",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: source_shape_probe.py PINNED_COPTIC_CORPORA_ROOT")
    print(json.dumps(audit(Path(sys.argv[1])), sort_keys=True, ensure_ascii=False))
