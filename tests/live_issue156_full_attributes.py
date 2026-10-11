"""Pinned source-byte parity of every gap/supplied/abbr opening and closing.

Compare independent raw-TT positional scanning against the parser's
source-ordered, per-attribute native annotation model. No corpus sidecars
or contents are published.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.parser import (
    TAG_RE, _scan_attrs, _visible_piece, parse_tt_record,
)
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph, _source_attr_feature_name
from tf.fabric import Fabric

SOURCE_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS = {"gap", "supplied", "abbr"}
EXPECTED = {"gap": 1162, "supplied": 1865, "abbr": 1620}
EXPECTED_RECORDS = 2628
EXPECTED_BLOBS = 565


def scan(raw: bytes, source: str):
    """Independent, tag-local scan with normalized word character offsets."""
    value = raw.decode("utf-8")
    closed_words = 0
    in_norm = False
    char_offset = 0
    cursor = 0
    events: list[dict[str, object]] = []
    opened: dict[str, list[dict[str, object]]] = {kind: [] for kind in KINDS}
    for m in TAG_RE.finditer(value):
        if in_norm:
            char_offset += len(_visible_piece(value[cursor:m.start()]))
        cursor = m.end()
        name, closing = m.group(2), bool(m.group(1))
        if name == "norm":
            if closing:
                assert in_norm, (source, "norm closed without opening")
                in_norm = False
                closed_words += 1
            else:
                assert not in_norm, (source, "nested norm")
                in_norm = True
                char_offset = 0
        if name not in KINDS:
            continue
        if not closing:
            attrs, _ = _scan_attrs(m.group(3))
            row = {
                "kind": name,
                "attributes": tuple(sorted(attrs.items())),
                "start_word_ordinal": closed_words+1 if in_norm else None,
                "start_char": char_offset if in_norm else None,
                "start_after_word_ordinal": closed_words,
            }
            opened[name].append(row)
            events.append(row)
        else:
            if not opened[name]:
                raise AssertionError(f"unmatched {name} in {source}")
            row = opened[name].pop()
            row.update(
                end_word_ordinal=closed_words+1 if in_norm else None,
                end_char=char_offset if in_norm else None,
                end_after_word_ordinal=closed_words,
            )
    if any(opened.values()):
        raise AssertionError(f"unclosed source editorial wrapper in {source}")
    return events


def sources(root: Path):
    files = sorted(
        p for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    )
    assert len(files) == EXPECTED_BLOBS, f"unexpected TT blob count {len(files)}"
    for file in files:
        parts = file.relative_to(root).parts
        if len(parts) == 3 and parts[1].endswith("_TT") and file.suffix == ".tt":
            dataset = parts[1].removesuffix("_TT")
            yield f"{parts[0]}/{dataset}:{file.stem}", file.relative_to(root).as_posix(), file.read_bytes(), "directory"
        elif len(parts) == 2 and file.name.endswith("_TT.zip"):
            dataset = file.name.removesuffix("_TT.zip")
            with ZipFile(file) as archive:
                for member in archive.infolist():
                    if member.is_dir() or not member.filename.lower().endswith(".tt"):
                        continue
                    rel = file.relative_to(root).as_posix()
                    yield f"{parts[0]}/{dataset}:{Path(member.filename).stem}", f"{rel}!{member.filename}", archive.read(member), "archive"
        else:
            raise AssertionError(f"unexpected pinned sparse source path {file}")


def assert_parity(doc, events):
    actual = [
        annotation for annotation in doc.editorial_annotations
        if annotation.kind in KINDS
    ]
    assert len(actual) == len(events), (doc.source_record_id, len(actual), len(events))
    for expected, seen in zip(events, actual):
        for field in (
            "kind", "attributes", "start_word_ordinal", "start_char",
            "start_after_word_ordinal", "end_word_ordinal", "end_char",
            "end_after_word_ordinal",
        ):
            assert getattr(seen, field) == expected[field], (
                doc.source_record_id, seen.ordinal, field,
                getattr(seen, field), expected[field],
            )


def assert_native(doc):
    graph = build_graph([doc])
    events = {
        (node.otype, node.source_ordinal): node
        for node in graph.nodes if node.otype in KINDS
    }
    for item in doc.editorial_annotations:
        if item.kind in KINDS:
            assert events[(item.kind, item.ordinal)].source_attributes == item.attributes
    with TemporaryDirectory(prefix="issue156-native-") as temp:
        directory = Path(temp) / "tf"
        write_graph(graph, directory)
        feature_names = sorted({
            _source_attr_feature_name(item.kind, key)
            for item in doc.editorial_annotations if item.kind in KINDS
            for key, _ in item.attributes
        })
        api = Fabric(locations=[str(directory)], silent="deep").load(
            "source_record_id source_ordinal " + " ".join(feature_names),
            silent="deep",
        )
        assert api and api.F.otype.maxSlot == len(doc.words)
        for item in doc.editorial_annotations:
            if item.kind not in KINDS:
                continue
            matches = [
                n for n in api.F.otype.s(item.kind)
                if api.F.source_ordinal.v(n) == item.ordinal
            ]
            assert len(matches) == 1, (doc.source_record_id, item.kind, item.ordinal)
            for key, literal in item.attributes:
                feature = _source_attr_feature_name(item.kind, key)
                assert getattr(api.F, feature).v(matches[0]) == literal, (
                    doc.source_record_id, item.kind, key, literal,
                )


def main(root: Path) -> None:
    counters = Counter()
    keys = Counter()
    records = 0
    examples = {}
    for record_id, path, raw, packaging in sources(root):
        records += 1
        events = scan(raw, path)
        doc = parse_tt_record(
            raw, source_record_id=record_id, source_path=path,
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=SOURCE_COMMIT, packaging=packaging,
        )
        assert_parity(doc, events)
        for item in events:
            counters[item["kind"]] += 1
            for key, _ in item["attributes"]:
                keys[f'{item["kind"]}.{key}'] += 1
            if item["kind"] not in examples:
                examples[item["kind"]] = doc
    assert records == EXPECTED_RECORDS, (records, EXPECTED_RECORDS)
    assert dict(counters) == EXPECTED, (counters, EXPECTED)
    assert set(examples) == KINDS, set(examples)
    for kind, doc in sorted(examples.items()):
        assert_native(doc)
    print(json.dumps({
        "source_commit": SOURCE_COMMIT,
        "source_records": records,
        "source_tt_git_blobs": EXPECTED_BLOBS,
        "original_wrappers": dict(counters),
        "attribute_key_occurrences": dict(sorted(keys.items())),
        "native_sample_kinds": sorted(examples),
        "interpretation": "exact original attribute and boundary parity; not reconstructed text",
    }, sort_keys=True), flush=True)
    print("PASS all 4647 original gap/supplied/abbr attributes and source positions preserved", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue156_full_attributes.py PINNED_TT_SOURCE")
    main(Path(sys.argv[1]))
