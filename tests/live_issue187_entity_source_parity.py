"""Pinned original entity.text attribute vs parser and full TF evidence (#187).

This script never prints original Coptic lexical content or any complete source
record. The native value comparison is done internally against raw TT bytes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from html import unescape
from pathlib import Path
import re

from copticscriptorium_tf.parser import parse_tt_record

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
REL = Path("doc-papyri/doc.papyri_TT/cpr.31.14.tt")
RECORD = "doc-papyri/doc.papyri:cpr.31.14"
OPEN = re.compile(r"<entity\s+([^>]*?)>")
ATTR = re.compile(r'\s+([A-Za-z_][A-Za-z0-9_.:-]*)="([^"]*)"')


def inspect(root: Path, native: Path | None) -> None:
    raw = (root / REL).read_bytes()
    source = raw.decode("utf-8")
    observed = []
    for match in OPEN.finditer(source):
        attrs = {key: unescape(value) for key, value in ATTR.findall(" " + match.group(1))}
        assert set(attrs) == {"entity", "head_tok", "text"}, (
            "pinned original entity attribute keys unexpectedly changed"
        )
        observed.append(attrs["text"])
    assert len(observed) == 12, "original pinned entity opening count drifted"
    parsed = parse_tt_record(
        raw, source_record_id=RECORD, source_path=REL.as_posix(),
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )
    assert len(parsed.entities) == 12, "parser dropped original entity"
    assert [e.source_text_literal for e in parsed.entities] == observed, (
        "parser lost original entity.text value/order"
    )
    assert all(e.word_ordinals for e in parsed.entities), "entity lost measured word locus"
    if native is not None:
        from tf.fabric import Fabric
        api = Fabric(locations=[str(native)], silent="deep").load(
            "source_attr_entity_text source_record_id source_sha256 source_ordinal",
            silent="deep",
        )
        assert api, "cannot reload full native TF"
        assert api.F.otype.maxSlot == 2_394_354
        assert len(api.F.otype.s("document")) == 2_628
        document = api.T.nodeFromSection((RECORD,))
        assert document is not None
        assert api.F.source_sha256.v(document) == sha256(raw).hexdigest()
        nodes = [n for n in api.F.otype.s("entity")
                 if api.F.source_record_id.v(n) == RECORD]
        assert len(nodes) == len(observed), "native entity count changed"
        assert [api.F.source_attr_entity_text.v(n) for n in nodes] == observed, (
            "native original entity text values/order differ from raw source"
        )
        start = min(api.E.oslots.s(document))
        for index, (node, entity) in enumerate(zip(nodes, parsed.entities), 1):
            assert api.F.source_ordinal.v(node) == entity.ordinal == index
            assert tuple(api.E.oslots.s(node)) == tuple(
                start + ordinal - 1 for ordinal in entity.word_ordinals
            ), "native entity Coptic word locus drifted"
    print("PASS original pinned entity attribute conservation",
          f"records=1 original_entity_text_openings={len(observed)}",
          f"native_reload={native is not None}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--native", type=Path)
    args = parser.parse_args()
    inspect(args.upstream, args.native)
