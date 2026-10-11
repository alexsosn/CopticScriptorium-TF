"""Pinned source-byte parity of every gap/supplied/abbr opening and closing.

Compare independent raw-TT positional scanning against the parser's
source-ordered, per-attribute native annotation model. No corpus sidecars
or contents are published.
"""
from __future__ import annotations

from collections import Counter
import html
import json
import re
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.parser import TAG_RE, _visible_piece, parse_tt_record

# Independently parse the original TT opening attributes: do not reuse
# production _scan_attrs, whose mistakes this regression is meant to catch.
_ORIGINAL_ATTR = re.compile(r'\s+([A-Za-z_][A-Za-z0-9_.:-]*)\s*=\s*"([^"]*)"')


def original_attributes(raw: str) -> tuple[tuple[str, str], ...]:
    values = []
    pos = 0
    while pos < len(raw):
        if not raw[pos:].strip():
            break
        match = _ORIGINAL_ATTR.match(raw, pos)
        if match is None:
            raise AssertionError(f"malformed source wrapper attribute at {pos}")
        values.append((match[1], html.unescape(match[2])))
        pos = match.end()
    if len(set(key for key, _ in values)) != len(values):
        raise AssertionError("duplicate original TT source attribute")
    return tuple(sorted(values))
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph, _source_attr_feature_name
from tf.fabric import Fabric

SOURCE_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS = {"gap", "supplied", "abbr"}
EXPECTED = {"gap": 1162, "supplied": 1865, "abbr": 1620}
EXPECTED_KEYS = {
    "gap.extent", "gap.gap", "gap.reason", "gap.unit",
    "supplied.reason", "supplied.source", "supplied.supplied",
    "abbr.type",
}
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
            attrs = original_attributes(m.group(3))
            row = {
                "kind": name,
                "attributes": attrs,
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
    if not events:
        return
    # This extra phase is essential: matching raw bytes to a parser model
    # does not prove that the graph kept every annotation node/attribute.
    graph = build_graph([doc])
    observed = {
        (node.otype, node.source_ordinal): node
        for node in graph.nodes if node.otype in KINDS
    }
    assert len(observed) == len(events), (doc.source_record_id, "native graph node loss")
    for ann in actual:
        node = observed.get((ann.kind, ann.ordinal))
        assert node is not None, (doc.source_record_id, ann.kind, ann.ordinal)
        assert node.source_attributes == ann.attributes, (
            doc.source_record_id, ann.kind, ann.ordinal,
        )
        assert node.start_char == ann.start_char and node.end_char == ann.end_char
        assert node.start_after_word_ordinal == ann.start_after_word_ordinal
        assert node.end_after_word_ordinal == ann.end_after_word_ordinal


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
        for item in doc.editorial_annotations:
            if item.kind not in KINDS:
                continue
            for key, _ in item.attributes:
                feature = _source_attr_feature_name(item.kind, key)
                raw_feature = (directory / f"{feature}.tf").read_text(encoding="utf-8")
                header = raw_feature.split("\n\n", 1)[0]
                assert f"@sourceTag={item.kind}" in header, (doc.source_record_id, feature)
                assert f"@sourceKey={key}" in header, (doc.source_record_id, feature)
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
            examples.setdefault((item["kind"], None), doc)
            for key, _ in item["attributes"]:
                examples.setdefault((item["kind"], key), doc)
    assert records == EXPECTED_RECORDS, (records, EXPECTED_RECORDS)
    assert dict(counters) == EXPECTED, (counters, EXPECTED)
    assert set(keys) == EXPECTED_KEYS, (set(keys), EXPECTED_KEYS)
    assert all((tag, None) in examples for tag in KINDS)
    assert all((tag, key) in examples
               for tag, key in (item.split(".", 1) for item in EXPECTED_KEYS))
    # A native TF reload is required for each *distinct original source key*
    # (plus a type sample). Cache repeated documents, not generated corpora.
    seen_records = set()
    for (_kind, _key), doc in sorted(
        examples.items(), key=lambda pair: (pair[0][0], pair[0][1] or "")
    ):
        if doc.source_record_id not in seen_records:
            assert_native(doc)
            seen_records.add(doc.source_record_id)
    print(json.dumps({
        "source_commit": SOURCE_COMMIT,
        "source_records": records,
        "source_tt_git_blobs": EXPECTED_BLOBS,
        "original_wrappers": dict(counters),
        "attribute_key_occurrences": dict(sorted(keys.items())),
        "native_sample_source_records": len(seen_records),
        "verified_original_source_attribute_keys": sorted(keys),
        "interpretation": "exact original attribute and boundary parity; not reconstructed text",
    }, sort_keys=True), flush=True)
    print("PASS all 4647 original gap/supplied/abbr attributes and source positions preserved", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue156_full_attributes.py PINNED_TT_SOURCE")
    main(Path(sys.argv[1]))
