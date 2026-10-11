"""Source-conservation census over every pinned TT directory and ZIP record.

Streams one physical record at a time, avoiding a multi-million-word in-memory
graph. Compares independently scanned annotation literals to the normalized
source model. Emits counts/paths only, never Greek passages or Coptic text.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import zipfile

from copticscriptorium_tf.parser import TAG_RE, _scan_attrs, parse_tt_record

COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS = frozenset(("sbl_greek", "sbl_apparatus"))


def records(root: Path):
    for directory in sorted(root.rglob("*_TT")):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f"invalid TT directory {directory}")
        relative = directory.relative_to(root)
        if len(relative.parts) != 2:
            raise ValueError(f"unexpected TT dataset path {relative}")
        corpus, dataset = relative.parts[0], relative.parts[1][:-3]
        for path in sorted(directory.glob("*.tt")):
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"invalid TT member {path}")
            name = path.stem
            yield f"{corpus}/{dataset}:{name}", path.relative_to(root).as_posix(), path.read_bytes(), "directory"
    for path in sorted(root.rglob("*_TT.zip")):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"invalid TT archive {path}")
        relative = path.relative_to(root)
        if len(relative.parts) != 2:
            raise ValueError(f"unexpected TT archive path {relative}")
        corpus, dataset = relative.parts[0], relative.parts[1][:-7]
        prefix = f"{dataset}_TT/"
        with zipfile.ZipFile(path) as archive:
            for member in sorted(archive.namelist()):
                if member.endswith("/") or not member.casefold().endswith(".tt"):
                    continue
                logical = member[len(prefix):] if member.startswith(prefix) else member
                if "/" in logical or not logical:
                    raise ValueError(f"unexpected TT archive member {member}")
                yield f"{corpus}/{dataset}:{logical[:-3]}", (
                    f"{relative.as_posix()}!/{member}"
                ), archive.read(member), "archive"


def expected_sbl(raw: bytes):
    text = raw.decode("utf-8")
    result = []
    for tag in TAG_RE.finditer(text):
        kind = tag.group(2)
        if tag.group(1) or kind not in KINDS:
            continue
        attrs, _ = _scan_attrs(tag.group(3))
        if kind not in attrs:
            raise ValueError(f"source SBL tag missing {kind} value")
        result.append((kind, attrs[kind]))
    return result


def audit(root: Path, *, expected_records: int = 2628) -> dict:
    physical = 0
    annotated = 0
    by_kind = Counter()
    by_packaging = Counter()
    by_corpus = Counter()
    spans = Counter()
    blank = Counter()
    examples = []
    seen = set()
    for identity, path, raw, packaging in records(root):
        identity_folded = identity.casefold()
        if identity_folded in seen:
            raise ValueError(f"duplicate physical TT record {identity}")
        seen.add(identity_folded)
        physical += 1
        by_packaging[packaging] += 1
        expected = expected_sbl(raw)
        if not expected:
            continue
        annotated += 1
        if len(examples) < 12:
            examples.append({"source_path": path, "annotations": len(expected)})
        doc = parse_tt_record(raw, source_record_id=identity,
            source_path=path, packaging=packaging,
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=COMMIT)
        observed = [(a.kind, a.value) for a in doc.sbl_annotations]
        if observed != expected:
            raise ValueError(f"SBL source/model occurrence mismatch at {identity}")
        for annotation in doc.sbl_annotations:
            by_kind[annotation.kind] += 1
            by_corpus[doc.corpus] += 1
            spans["sbl_span" if annotation.word_ordinals else "sbl_anchor"] += 1
            if annotation.value == "":
                blank[annotation.kind] += 1
    if physical != expected_records:
        raise ValueError(f"pinned TT physical record count changed: {physical} != {expected_records}")
    if not by_kind["sbl_greek"]:
        raise ValueError("pinned source SBL Greek annotations disappeared")
    return {
        "status": "pass",
        "upstream_commit": COMMIT,
        "physical_records": physical,
        "annotated_physical_records": annotated,
        "packaging": dict(sorted(by_packaging.items())),
        "annotation_occurrences": dict(sorted(by_kind.items())),
        "annotation_occurrences_by_corpus": dict(sorted(by_corpus.items())),
        "source_locus_classes": dict(sorted(spans.items())),
        "present_empty_values": dict(sorted(blank.items())),
        "source_path_examples": examples,
        "scope": "Pinned TT directories and ZIP physical records; one-record-at-a-time source/model preservation, not full TF release",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.source_root)
    payload = json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
