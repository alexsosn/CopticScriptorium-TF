"""Independent original TT opening tags vs parser and full native TF (#184).

No upstream Arabic/Coptic literal is logged or redistributed. This is pinned
source evidence, not a generic claim that other TT attributes are conserved.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import html
from pathlib import Path
import re

from copticscriptorium_tf.parser import parse_tt_record

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KIND_PATTERN = re.compile(r"<(arabic|arabic_translation)\s+([^>]*?)>")
ATTR_PATTERN = re.compile(r'\s+([a-z_]+)="([^"]*)"')
FILES = {
    "AP/apophthegmata.patrum_TT/AP.044.w670.temptation.tt": (
        "AP/apophthegmata.patrum:AP.044.w670.temptation",
        Counter({"arabic_translation": 3}),
    ),
    "AP/apophthegmata.patrum_TT/AP.054.daniel.04.tt": (
        "AP/apophthegmata.patrum:AP.054.daniel.04",
        Counter({"arabic": 5}),
    ),
}


def audit(root: Path, native: Path | None):
    api = None
    if native is not None:
        from tf.fabric import Fabric
        api = Fabric(locations=[str(native)], silent="deep").load(
            "original_source_tag source_record_id source_sha256 own_text",
            silent="deep",
        )
        if not api:
            raise AssertionError("full native TF failed clean reload")
        assert api.F.otype.maxSlot == 2_394_354
        assert len(api.F.otype.s("document")) == 2_628

    for relative, (record_id, expected) in FILES.items():
        source = (root / relative).read_bytes()
        source_text = source.decode("utf-8")
        scanned = []
        for match in KIND_PATTERN.finditer(source_text):
            kind = match.group(1)
            attrs = {key: html.unescape(value) for key, value
                     in ATTR_PATTERN.findall(" " + match.group(2))}
            assert set(attrs) == {kind}, "unexpected original Arabic attributes"
            scanned.append((kind, attrs[kind]))
        assert Counter(tag for tag, _ in scanned) == expected, (
            "original Arabic tag counts drift from pinned source"
        )
        doc = parse_tt_record(
            source, source_record_id=record_id, source_path=relative,
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        assert [(a.source_tag, a.text) for a in doc.arabic_translations] == scanned, (
            "parser lost original Arabic source kind/value/order"
        )
        if api is not None:
            d = api.T.nodeFromSection((record_id,))
            assert d is not None, "physical document section missing in native TF"
            assert api.F.source_sha256.v(d) == sha256(source).hexdigest(), (
                "native original source byte digest mismatch"
            )
            nodes = [node for node in api.F.otype.s("arabic_translation")
                     if api.F.source_record_id.v(node) == record_id]
            assert len(nodes) == len(scanned)
            assert [(api.F.original_source_tag.v(node), api.T.text(node))
                    for node in nodes] == scanned, "native original tag/value parity failed"
            assert len(tuple(api.E.oslots.s(d))) == len(doc.words)
        print(
            f"PASS pinned Arabic source kind/value order record={record_id} "
            f"counts={dict(expected)} native_reload={api is not None}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--native", type=Path)
    opts = parser.parse_args()
    audit(opts.upstream, opts.native)
