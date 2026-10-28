"""#189: independent pinned raw morph.lang evidence vs reloaded native TF.

Original labels and words stay private inside assertions: CI reports aggregate
counts and source IDs only. The native scanner never synthesizes lang labels.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from html import unescape
from pathlib import Path
import re
from zipfile import ZipFile

from copticscriptorium_tf.parser import parse_tt_record

# Deliberately independent of parser.TAG_RE, parser._scan_attrs and model
# wrapper declarations: comparing a parser against itself is not source parity.
RAW_TAG = re.compile(r"<(/?)([A-Za-z_][A-Za-z0-9_.:-]*)([^>]*)>")
RAW_ATTR = re.compile(r'\s+([A-Za-z_][A-Za-z0-9_.:-]*)\s*=\s*"([^"]*)"')
TOKEN_SOURCE_TAGS = frozenset(
    ("morph", "norm_func", "norm_head", "norm_xml:id", "norm_new_sent")
)


def original_attrs(fragment: str):
    observed = {}
    offset = 0
    while offset < len(fragment):
        if not fragment[offset:].strip():
            break
        match = RAW_ATTR.match(fragment, offset)
        assert match is not None, "malformed original source attribute"
        key = match.group(1)
        assert key not in observed, "duplicate original source attribute"
        observed[key] = unescape(match.group(2))
        offset = match.end()
    return observed

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
SAMPLE = {
    "sahidic.ot/sahidic.ot:01_Genesis_01",
    "sahidic.ot/sahidic.ot:01_Genesis_05",
    "sahidic.ot/sahidic.ot:01_Genesis_17",
}


def original_records(root: Path):
    direct = sorted(root.glob("*/*_TT/*.tt"))
    archives = sorted(root.glob("*/*_TT.zip"))
    assert len(direct) + len(archives) == 565, "unexpected pinned TT blob inventory"
    for file in direct:
        rel = file.relative_to(root)
        corpus, dataset_dir, filename = rel.parts
        assert dataset_dir.endswith("_TT")
        dataset = dataset_dir[:-3]
        yield (f"{corpus}/{dataset}:{filename[:-3]}", rel.as_posix(),
               file.read_bytes(), "directory")
    for file in archives:
        rel = file.relative_to(root)
        corpus, archive_filename = rel.parts
        dataset = archive_filename[:-7]
        with ZipFile(file) as archive:
            for member in sorted(archive.namelist()):
                if member.endswith("/") or not member.casefold().endswith(".tt"):
                    continue
                prefix = f"{dataset}_TT/"
                logical = member[len(prefix):] if member.startswith(prefix) else member
                assert "/" not in logical and logical.endswith(".tt")
                yield (f"{corpus}/{dataset}:{logical[:-3]}",
                       f"{rel.as_posix()}!/{member}", archive.read(member), "archive")


def compare(root: Path, native: Path | None):
    expected = {}
    source_digests = {}
    original_records_count = 0
    seen_samples = set()
    for record_id, relative, raw, packaging in original_records(root):
        original_records_count += 1
        ordinal = 0
        attested = []
        text = raw.decode("utf-8")
        for m in RAW_TAG.finditer(text):
            if m.group(1) or m.group(2) not in TOKEN_SOURCE_TAGS:
                continue
            ordinal += 1
            if m.group(2) == "morph":
                attrs = original_attrs(m.group(3))
                assert set(attrs) in ({"morph"}, {"morph", "lang"})
                if "lang" in attrs:
                    entry = (record_id, ordinal)
                    assert entry not in expected
                    expected[entry] = (attrs["morph"], attrs["lang"])
                    attested.append((ordinal, attrs["morph"], attrs["lang"]))
        if attested:
            source_digests[record_id] = sha256(raw).hexdigest()
            parsed = parse_tt_record(
                raw, source_record_id=record_id, source_path=relative,
                upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN,
                packaging=packaging,
            )
            by_ordinal = {a.ordinal: a for a in parsed.token_annotations if a.kind == "morph"}
            for occurrence, original_morph, original_lang in attested:
                assert occurrence in by_ordinal
                item = by_ordinal[occurrence]
                assert item.value == original_morph
                assert dict(item.source_attributes) == {"morph": original_morph, "lang": original_lang}
            if record_id in SAMPLE:
                seen_samples.add(record_id)

    assert original_records_count == 2628, original_records_count
    assert len(expected) == 284, "original morph.lang source counts differ from pinned census"
    assert seen_samples == SAMPLE, "pinned Genesis original witnesses missing"

    if native is not None:
        from tf.fabric import Fabric
        api = Fabric(locations=[str(native)], silent="deep").load(
            "source_attr_morph_lang source_record_id source_ordinal source_sha256 value",
            silent="deep",
        )
        assert api, "native TF load failed"
        assert api.F.otype.maxSlot == 2_394_354
        assert len(api.F.otype.s("document")) == 2_628
        seen = set()
        total_morph = 0
        for node in api.F.otype.s("morph"):
            total_morph += 1
            key = (api.F.source_record_id.v(node), api.F.source_ordinal.v(node))
            lang = api.F.source_attr_morph_lang.v(node)
            if key in expected:
                original_morph, original_lang = expected[key]
                assert lang == original_lang, "native morph.lang differs from original literal"
                assert api.F.value.v(node) == original_morph, "native morph value changed"
                assert tuple(api.E.oslots.s(node)), "morph must retain its native word slot"
                seen.add(key)
            else:
                assert lang is None, "native invented morph.lang on source without attribute"
        assert seen == set(expected), "source morph.lang occurrence lost after native reload"
        assert total_morph == 78_265, "native morph count drift"
        for record_id, digest in source_digests.items():
            doc = api.T.nodeFromSection((record_id,))
            assert doc is not None
            assert api.F.source_sha256.v(doc) == digest, "source byte SHA mismatch"
    print("PASS original pinned morph.lang source parity",
          f"physical_records={original_records_count} labels={len(expected)}",
          f"source_records={len(source_digests)} native_reload={native is not None}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("upstream", type=Path)
    p.add_argument("--native", type=Path)
    opts = p.parse_args()
    compare(opts.upstream, opts.native)
