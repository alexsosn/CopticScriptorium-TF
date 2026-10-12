"""Full pinned source parity for all nine entity/name-label wrapper types (#159).

This is source-shape conservation (not entity linking or ontology resolution).
Reads direct TT files and archive members one at a time, emits counts only.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath
import json
import re
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copticscriptorium_tf.model import ENTITY_LABEL_WRAPPER_TYPES
from copticscriptorium_tf.parser import TAG_RE, parse_tt_record
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph
from tf.fabric import Fabric
from tempfile import TemporaryDirectory

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
EXPECTED = {
    "entity_head_tok": 3677, "entity_text": 3677, "entity_identity": 901,
    "persName_type": 245, "placeName_type": 140, "placeName_ref": 85,
    "roleName_type": 80, "rs_type": 18, "org_type": 4,
}
FOCUS = {
    "life-aphou/life.aphou_TT/life.aphou.01.tt",
    "abraham/shenoute.abraham_TT/YA525-530.tt",
    "john-constantinople/john.constantinople_TT/penitence.01.tt",
}
PLAIN = re.compile(r"^[^/]+/[^/]+_TT/[^/]+\.tt$")
ARCHIVE = re.compile(r"^[^/]+/[^/]+_TT\.zip$")


def scan(raw: bytes, source_record_id: str, source_path: str, packaging: str):
    text = raw.decode("utf-8-sig")
    original = Counter(
        m.group(2) for m in TAG_RE.finditer(text)
        if not m.group(1) and m.group(2) in EXPECTED
    )
    doc = parse_tt_record(
        raw, source_record_id=source_record_id, source_path=source_path,
        packaging=packaging, upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )
    parsed = Counter(a.kind for a in doc.entity_label_annotations)
    if original != parsed:
        raise AssertionError(
            f"source loss in {source_path}: original={original} parsed={parsed}"
        )
    for ann in doc.entity_label_annotations:
        if ann.start_after_word_ordinal > ann.end_after_word_ordinal:
            raise AssertionError(f"inverted occurrence in {source_path}: {ann.kind}")
    return doc, original


def main(root: Path):
    files = sorted(p for p in root.rglob("*") if p.is_file()
                   and ".git" not in p.relative_to(root).parts)
    assert len(files) == 565, f"unexpected sparse Git blob count {len(files)}"
    counts = Counter()
    samples = []
    records = 0
    word_slots = 0
    for file in files:
        rel = file.relative_to(root).as_posix()
        if PLAIN.fullmatch(rel):
            corpus = rel.split("/", 1)[0]
            dataset = PurePosixPath(rel).parts[1].removesuffix("_TT")
            record = file.stem
            doc, observed = scan(
                file.read_bytes(), f"{corpus}/{dataset}:{record}", rel, "directory"
            )
            counts.update(observed)
            records += 1
            word_slots += len(doc.words)
            if rel in FOCUS:
                samples.append(doc)
        elif ARCHIVE.fullmatch(rel):
            corpus = rel.split("/", 1)[0]
            dataset = file.name.removesuffix("_TT.zip")
            with ZipFile(file) as archive:
                for item in archive.infolist():
                    if item.is_dir() or not item.filename.lower().endswith(".tt"):
                        continue
                    name = PurePosixPath(item.filename).stem
                    doc, observed = scan(
                        archive.read(item),
                        f"{corpus}/{dataset}:{name}",
                        f"{rel}!{item.filename}", "archive",
                    )
                    counts.update(observed)
                    records += 1
                    word_slots += len(doc.words)
        else:
            raise AssertionError(f"unanticipated pinned TT source path {rel}")

    assert records == 2628, (records, "pinned source record count")
    assert word_slots == 2394354, (word_slots, "canonical word slots changed")
    assert counts == Counter(EXPECTED), (dict(counts), EXPECTED)
    assert len(samples) == len(FOCUS), "missing real crossed/nested source witnesses"
    # Narrow, independently pinned examples are intentionally NOT a complete
    # scholarly witness collection. Auto-derived witness CTS edges demand the
    # referenced physical records and appropriately fail on this subset.
    # The gate below tests label-node conservation, not document witnesses;
    # do not forge external witness targets into this three-record graph.
    graph = build_graph(samples, document_relations=())
    assert len(graph.slots) == sum(len(doc.words) for doc in samples)
    with TemporaryDirectory(prefix="issue159-native-") as temp:
        output = Path(temp) / "tf"
        write_graph(graph, output)
        api = Fabric(locations=[str(output)], silent="deep").load(
            "source_record_id value render_mode source_ordinal start_word_ordinal"
            " start_char end_word_ordinal end_char", silent="deep"
        )
        assert api is not None, "real source native TF reload failed"
        for kind in ENTITY_LABEL_WRAPPER_TYPES:
            actual = sum(1 for d in samples for a in d.entity_label_annotations if a.kind == kind)
            assert len(api.F.otype.s(kind)) == actual, (kind, actual)
        paths_refs = [
            api.F.value.v(n) for n in api.F.otype.s("placeName_ref")
        ]
        assert "paths:places:32" in paths_refs, paths_refs
        assert any(api.F.value.v(n) == "Sarah" for n in api.F.otype.s("entity_identity"))
        # Third independently acquired real witness exercises the large
        # entity-head/token-text wrapper family, not only synthetic fixtures.
        assert api.F.otype.s("entity_head_tok")
        assert api.F.otype.s("entity_text")
        assert api.F.otype.maxSlot == len(graph.slots)
    print(json.dumps({
        "source_commit": PIN,
        "raw_git_blobs": len(files),
        "physical_tt_records": records,
        "word_slots": word_slots,
        "entity_label_source_openings": sum(counts.values()),
        "entity_label_counts": dict(sorted(counts.items())),
        "native_tf_real_samples": len(samples),
        "interpretation": "raw entity/name labels only; no ontology or textual alignment",
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue159_source_parity.py PINNED_TT_ROOT")
    main(Path(sys.argv[1]))
