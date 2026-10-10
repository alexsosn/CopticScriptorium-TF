"""Full pinned Coptic→LXX native reference-candidate modules (issue #82).

Full Coptic TF warp must be produced from *the same exact source* used by
this one-pass iterator. No original TT data, translations, or generated corpus
are published to GitHub. This is an operational candidate-address audit only.
"""
from __future__ import annotations

from collections import Counter
import gc
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copticscriptorium_tf.converter import convert_source_tree
from copticscriptorium_tf.lxx_module import (
    COPTIC_PIN, LXX_PIN, materialize_lxx_reference_modules_streaming,
    verify_coptic_module_parent, verify_lxx_parent_feature_blobs,
)
from copticscriptorium_tf.parser import parse_tt_record

DIRECT = re.compile(r"^[^/]+/[^/]+_TT/[^/]+\.tt$")
ARCHIVE = re.compile(r"^[^/]+/[^/]+_TT\.zip$")


def iter_source_records(root: Path):
    """Parse each Coptic document individually, including exact ZIP membership."""
    selected = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.relative_to(root).parts:
            continue
        rel = path.relative_to(root).as_posix()
        if not DIRECT.fullmatch(rel) and not ARCHIVE.fullmatch(rel):
            raise ValueError(f"non-TT sparse Git source file: {rel}")
        selected.append((rel, path))
    if len(selected) != 565:
        raise ValueError(f"pinned TT blob inventory changed: {len(selected)}")
    for rel, path in sorted(selected):
        corpus = rel.split("/", 1)[0]
        if ARCHIVE.fullmatch(rel):
            dataset = path.name.removesuffix("_TT.zip")
            with ZipFile(path) as archive:
                for entry in sorted(archive.infolist(), key=lambda e: e.filename):
                    if entry.is_dir() or not entry.filename.lower().endswith(".tt"):
                        continue
                    yield parse_tt_record(
                        archive.read(entry),
                        source_record_id=f"{corpus}/{dataset}:{Path(entry.filename).stem}",
                        source_path=f"{rel}!{entry.filename}",
                        upstream_repository="CopticScriptorium/corpora",
                        upstream_commit=COPTIC_PIN,
                        packaging="archive",
                    )
        else:
            dataset = path.parent.name.removesuffix("_TT")
            yield parse_tt_record(
                path.read_bytes(),
                source_record_id=f"{corpus}/{dataset}:{path.stem}",
                source_path=rel,
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit=COPTIC_PIN,
            )


def run(coptic_source: Path, greek_tf: Path, scratch: Path) -> None:
    if scratch.exists() or scratch.is_symlink():
        raise ValueError(f"scratch destination already exists: {scratch}")
    scratch.mkdir(parents=True)
    coptic_tf = scratch / "coptic-tf"
    output_modules = scratch / "modules"
    verify_lxx_parent_feature_blobs(greek_tf)
    converted = convert_source_tree(
        coptic_source, coptic_tf,
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=COPTIC_PIN,
    )
    if converted.source_records != 2628 or converted.slots != 2394354:
        raise ValueError(f"unexpected complete pinned converter size: {converted}")

    coptic_api = Fabric(locations=[str(coptic_tf)], silent="deep").load(
        "source_record_id source_word_ordinal source_sha256", silent="deep"
    )
    greek_api = Fabric(locations=[str(greek_tf)], silent="deep").load(
        "book chapter verse subverse", silent="deep"
    )
    if not coptic_api or not greek_api:
        raise RuntimeError("failed to load Coptic/Greek parent native TF")
    result = materialize_lxx_reference_modules_streaming(
        documents=iter_source_records(coptic_source),
        coptic_api=coptic_api, lxx_api=greek_api,
        output_root=output_modules,
        lxx_parent_commit=LXX_PIN, coptic_source_commit=COPTIC_PIN,
        coptic_parent_tf=coptic_tf, lxx_parent_tf=greek_tf,
    )
    if result.source_documents != 2628 or result.coptic_status_words != 2394354:
        raise ValueError(f"incomplete source→Coptic parent mapping: {result}")
    if result.lxx_candidate_verses != 21120:
        raise ValueError(f"distinct Greek verse-address coverage regression: {result}")
    verify_coptic_module_parent(output_modules / "coptic", coptic_tf)

    # Release earlier loaded mapping APIs before fresh overlays to reduce peak
    # retained references. The TF warp remains on disk for independent reload.
    del coptic_api, greek_api
    gc.collect()
    coptic_overlay = Fabric(
        locations=[str(coptic_tf), str(output_modules / "coptic")],
        silent="deep",
    ).load("source_record_id coptic_lxx_ref_id coptic_lxx_ref_status", silent="deep")
    greek_overlay = Fabric(
        locations=[str(greek_tf), str(output_modules / "lxx")], silent="deep"
    ).load("coptic_lxx_ref_id", silent="deep")
    if not coptic_overlay or not greek_overlay:
        raise RuntimeError("native Coptic/Greek bilateral module reload failed")
    if coptic_overlay.F.otype.maxSlot != 2394354 or greek_overlay.F.otype.maxSlot != 623693:
        raise ValueError("bilateral module changed the parent word slot warp")
    statuses = Counter()
    coptic_keys: set[str] = set()
    for w in coptic_overlay.F.otype.s("word"):
        status = coptic_overlay.F.coptic_lxx_ref_status.v(w)
        if not status:
            raise ValueError(f"missing Coptic alignment status for physical word {w}")
        key = coptic_overlay.F.coptic_lxx_ref_id.v(w)
        if key:
            if status != "reference_candidate":
                raise ValueError("unresolved/unclassified word has fabricated Greek ID")
            coptic_keys.add(key)
        statuses[status] += 1
    greek_keys: set[str] = set()
    for node in greek_overlay.F.otype.s("verse"):
        key = greek_overlay.F.coptic_lxx_ref_id.v(node)
        if key:
            if key in greek_keys:
                raise ValueError("duplicate Greek verse for a shared Coptic reference")
            greek_keys.add(key)
    if coptic_keys != greek_keys or len(greek_keys) != 21120:
        raise ValueError("native Coptic/LXX reference modules disagree on Greek target set")
    if sum(statuses.values()) != 2394354:
        raise ValueError("missing Coptic word status after fresh TF overlay load")
    if statuses["unclassified_corpus"] <= 0 or statuses["unresolved"] <= 0:
        raise ValueError("incomplete unresolved/unclassified candidate provenance")
    print(json.dumps({
        "stage": "full-pinned-streamed-dual-native-TF-modules",
        "coptic_source_records": result.source_documents,
        "coptic_word_slots": converted.slots,
        "coptic_candidate_words": result.coptic_candidate_words,
        "distinct_candidate_lxx_verse_nodes": result.lxx_candidate_verses,
        "word_statuses": dict(sorted(statuses.items())),
        "lxx_release_commit": LXX_PIN,
        "source_commit": COPTIC_PIN,
        "parent_fingerprint_verified": True,
        "interpretation": "matching reference addresses ONLY; Greek-Coptic textual alignment NOT established",
    }, sort_keys=True), flush=True)
    print("PASS full pinned Coptic↔LXX streaming native weft reload and shared-reference identity")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: python tests/live_issue82_full_modules.py COPTIC_ROOT LXX_TF SCRATCH")
    run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
