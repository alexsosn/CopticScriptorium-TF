"""#214: source-attested Coptic TT v6.3.1 migration research + real TF smoke.

Read-only on immutable upstream old/new Git checkouts; build only a fresh TF
subset for the four changed physical originals. No copyrighted source text
is written to the report, uploaded or printed.

Run in an installed Python 3.12 wheel environment:
    python tests/live_issue214_v631_source_audit.py old checkout-new scratch
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from html import unescape
import json
from pathlib import Path
import re
import subprocess
import sys

OLD_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
NEW_COMMIT = "6fb51458e7156dd5387c2b2dca207aac1692e4d0"
UPSTREAM = "CopticScriptorium/corpora"

# Immutable Git *blob* digests derived independently from the official Git
# source comparison and fetched unchanged old source blobs. Do not confuse
# these Git SHA-1 object IDs with file-content SHA-256 TF provenance.
CHANGED_BLOBS = {
    "john-constantinople/john.constantinople_TT/penitence.01.tt": (
        "6295f5f3e1c065fec367de712aadac9a889acb8e",
        "075deeb8a97d9bd719bf3d36955574cdd32fe7f9",
    ),
    "john-constantinople/john.constantinople_TT/penitence.02.tt": (
        "08e8f3a686a4739aabe96ad93219cb10",
        "47a55e4e3b92e787361adc0da344049783a9b806",
    ),
    "proclus-homilies/proclus.homilies_TT/proclus.23.nativity.tt": (
        "9a4bf3e693dd4a6bbfa134e2f81b480c908ced2c",
        "26059003a40d8c8350c2bf74476b9f11336adcf1",
    ),
    "shenoute-those/shenoute.those_TT/shenoute.those.GL269-270.tt": (
        "f1729e61b8e7cc869dc7d5972b15ac3282859252",
        "b98fd33892c8c5f3275f8eaae5e9e6367553b96f",
    ),
}

# The official 6.3.1 correction removed only these fake wrappers; actual
# norm_group/orig_group/entity/translation/layout annotations stay untouched.
_REMOVABLE = frozenset(("norm_func", "norm_head", "norm_new_sent", "norm_xml:id"))
_SPURIOUS_LINE = re.compile(r"^<(\/)?(norm_(?:func|head|new_sent|xml:id))(?:\s[^>]*)?>\r?\n?$")
_NORM_OPEN = re.compile(r"^<norm(?=\s|>)([^>]*)>", flags=re.MULTILINE)
_NORM_LITERAL = re.compile(r'(?:^|\s)norm="([^"]*)"')
_META = re.compile(r"^<meta\s[^\n]*>", re.MULTILINE)


def _neutralize_root_version(text: str, *, release: bool) -> str:
    roots = list(_META.finditer(text))
    if len(roots) != 1:
        raise ValueError("expected one physical source root metadata opener")
    literal = roots[0].group()
    for name, expected in (
        ("version_n", "6.3.1" if release else None),
        ("version_date", "2026-10-26" if release else None),
    ):
        attr = re.compile(r'(?<!\S)' + name + r'="([^"]+)"')
        values = list(attr.finditer(literal))
        if len(values) != 1:
            raise ValueError("missing or duplicate original " + name)
        if expected is not None and values[0].group(1) != expected:
            raise ValueError("incorrect v6.3.1 source " + name)
        literal = attr.sub(f'{name}="<version>"', literal)
    return text[:roots[0].start()] + literal + text[roots[0].end():]


def compare_original_tt(old_raw: bytes, new_raw: bytes) -> dict[str, object]:
    """Certify the entire correction without trusting upstream release notes.

    All bytes other than exact whole-line spurious norm_* wrapper tags and the
    two original root version attributes must match. A changed word, nesting
    element, whitespace, annotation value, or other source line is fatal.
    """
    old = old_raw.decode("utf-8")
    new = new_raw.decode("utf-8")
    dropped = Counter()
    kept = []
    for line in old.splitlines(keepends=True):
        match = _SPURIOUS_LINE.fullmatch(line)
        if match is None:
            kept.append(line)
        else:
            name = match.group(2)
            assert name in _REMOVABLE
            dropped[(name, "close" if match.group(1) else "open")] += 1

    if not dropped:
        raise ValueError("old original has no spurious wrappers to correct")
    for name in _REMOVABLE:
        if dropped[(name, "open")] != dropped[(name, "close")]:
            raise ValueError("unbalanced removed source annotation wrapper " + name)

    clean_old = _neutralize_root_version("".join(kept), release=False)
    clean_new = _neutralize_root_version(new, release=True)
    if clean_old != clean_new:
        index = next(
            (i for i, (a, b) in enumerate(zip(clean_old, clean_new)) if a != b),
            min(len(clean_old), len(clean_new)),
        )
        # Report only an index, never a copyrighted source excerpt.
        raise ValueError("v6.3.1 changed material beyond permitted wrappers/meta at character " + str(index))

    old_norm = len(_NORM_OPEN.findall(old))
    new_norm = len(_NORM_OPEN.findall(new))
    if not old_norm or old_norm != new_norm:
        raise ValueError("v6.3.1 changed physical norm token count")
    if any(_SPURIOUS_LINE.fullmatch(line) for line in new.splitlines(keepends=True)):
        raise ValueError("corrected source still contains spurious wrappers")

    return {
        "original_norm_count": old_norm,
        "new_norm_count": new_norm,
        "removed_wrappers": {
            name: dropped[(name, "open")] + dropped[(name, "close")]
            for name in sorted(_REMOVABLE)
            if dropped[(name, "open")] or dropped[(name, "close")]
        },
        "retained_source_content": "exact",
    }


def _source_id(path: str) -> str:
    corpus, relative = path.split("/", 1)
    dataset = relative.split("/", 1)[0].removesuffix("_TT")
    return f"{corpus}/{dataset}:{Path(path).stem}"


def _original_norms(raw: bytes) -> tuple[str, ...]:
    text = raw.decode("utf-8")
    values = []
    for match in _NORM_OPEN.finditer(text):
        attr = _NORM_LITERAL.search(match.group(1))
        if attr is None:
            raise ValueError("source norm opener missing literal norm value")
        values.append(unescape(attr.group(1)))
    return tuple(values)


def _git_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, timeout=30,
    )
    return result.stdout.strip()


def _git_blob(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    return result.stdout.strip()


def audit_and_convert(old_root: Path, new_root: Path, scratch: Path) -> dict[str, object]:
    if _git_head(old_root) != OLD_COMMIT or _git_head(new_root) != NEW_COMMIT:
        raise ValueError("exact original Coptic source Git revision mismatch")
    if scratch.exists() or scratch.is_symlink():
        raise ValueError("output location already exists; refusing overwrite")
    scratch.mkdir(parents=True)
    old_norms = {}
    new_hashes = {}
    audited = {}
    for path, (old_blob, new_blob) in CHANGED_BLOBS.items():
        old = old_root / path
        new = new_root / path
        if not old.is_file() or not new.is_file() or old.is_symlink() or new.is_symlink():
            raise ValueError("missing or symlinked original TT record: " + path)
        if _git_blob(old) != old_blob or _git_blob(new) != new_blob:
            raise ValueError("Git blob identity of original TT record drifted: " + path)
        raw_before, raw_after = old.read_bytes(), new.read_bytes()
        audited[path] = compare_original_tt(raw_before, raw_after)
        sid = _source_id(path)
        old_norms[sid] = _original_norms(raw_before)
        assert old_norms[sid] == _original_norms(raw_after)
        new_hashes[sid] = sha256(raw_after).hexdigest()

    # Use the *public installed CLI*, not the parser or writer intermediate
    # representation. This exercises input discovery, graph build and TF write.
    output = scratch / "native-tf"
    summary = scratch / "summary.json"
    cmd = [
        "copticscriptorium-tf", str(new_root), str(output),
        "--upstream-repository", UPSTREAM,
        "--upstream-commit", NEW_COMMIT,
        "--summary", str(summary),
    ]
    process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if process.returncode:
        raise RuntimeError(
            "released TT original fails installed CLI, exit=" + str(process.returncode)
            + ", diagnostic_sha256=" + sha256(process.stderr.encode("utf-8", "replace")).hexdigest()[:20]
        )
    metrics = json.loads(summary.read_text(encoding="utf-8"))
    expect_count = sum(map(len, old_norms.values()))
    if metrics["source_records"] != len(CHANGED_BLOBS) or metrics["slots"] != expect_count:
        raise ValueError("released physical records/word slots failed original TT parity")

    # Compare *reloaded native TF*, including exact original per-word norm
    # literal values in source order, not the converter's intermediate model.
    from tf.fabric import Fabric

    api = Fabric(locations=[str(output)], silent="deep").load(
        "norm source_record_id source_word_ordinal source_sha256", silent="deep"
    )
    if not api:
        raise RuntimeError("released original TT failed native TF reload")
    documents = api.F.otype.s("document")
    words = api.F.otype.s("word")
    if len(documents) != 4 or len(words) != expect_count:
        raise ValueError("wrong native node types/counts after released TT conversion")

    seen_docs = {}
    for node in documents:
        sid = api.F.source_record_id.v(node)
        if sid in seen_docs:
            raise ValueError("duplicate physical source record in TF")
        if sid not in new_hashes or api.F.source_sha256.v(node) != new_hashes[sid]:
            raise ValueError("wrong original source sha256 or document identity in TF")
        if api.T.nodeFromSection((sid,)) != node:
            raise ValueError("original source section cannot be navigated after TF reload")
        seen_docs[sid] = node
    if set(seen_docs) != set(old_norms):
        raise ValueError("original release document identities changed")
    grouped = {key: [] for key in seen_docs}
    for node in words:
        sid = api.F.source_record_id.v(node)
        if sid not in grouped:
            raise ValueError("orphan word in released native TF")
        ordinal = api.F.source_word_ordinal.v(node)
        grouped[sid].append((ordinal, api.F.norm.v(node)))
    for sid, expected in old_norms.items():
        actual = tuple(value for ordinal, value in sorted(grouped[sid]))
        if actual != expected:
            raise ValueError("original Coptic norm literals changed in native TF: " + sid)

    return {
        "status": "PASS release-original-literal-v631-TF",
        "old_commit": OLD_COMMIT,
        "new_commit": NEW_COMMIT,
        "changed_physical_records": len(CHANGED_BLOBS),
        "changed_record_word_slots": expect_count,
        "exact_coptic_norm_parity": True,
        "original_document_sha256_parity": True,
        "native_TF_reload": True,
        "source_deltas": audited,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Audit source-to-TF Coptic v6.3.1 delta")
    p.add_argument("old", type=Path)
    p.add_argument("new", type=Path)
    p.add_argument("scratch", type=Path)
    args = p.parse_args()
    result = audit_and_convert(args.old, args.new, args.scratch)
    # Metadata and aggregate counts only, never raw TT text.
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
