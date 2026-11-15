"""#192: raw norm.lang source parity vs sparse native Text-Fabric word values.

Raw original opening/attr scanning is independent of the converter's tag and
attribute parsers. Values are compared in-memory and never printed in logs.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from html import unescape
from pathlib import Path
import re

from copticscriptorium_tf.parser import parse_tt_record
from live_issue189_morph_lang_parity import original_records

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
RAW_NORM = re.compile(r"<norm(?=\s|>)([^>]*)>")
RAW_ATTR = re.compile(r'\s+([A-Za-z_][A-Za-z0-9_.:-]*)\s*=\s*"([^"]*)"')


def original_attrs(fragment: str):
    values = {}
    at = 0
    while at < len(fragment):
        if not fragment[at:].strip():
            break
        found = RAW_ATTR.match(fragment, at)
        assert found is not None, "invalid original norm source attributes"
        key = found.group(1)
        assert key not in values, "duplicate original norm attr"
        values[key] = unescape(found.group(2))
        at = found.end()
    return values


def audit(root: Path, native: Path | None):
    expected = {}
    affected_digests = {}
    count_documents = 0
    count_norms = 0
    for record_id, path, raw, packaging in original_records(root):
        count_documents += 1
        source = raw.decode("utf-8")
        attested = []
        for ordinal, match in enumerate(RAW_NORM.finditer(source), 1):
            count_norms += 1
            attrs = original_attrs(match.group(1))
            assert "norm" in attrs, "pinned norm opener has no original norm"
            if "lang" in attrs:
                key = (record_id, ordinal)
                assert key not in expected, "duplicate physical original word key"
                expected[key] = (attrs["norm"], attrs["lang"])
                attested.append((ordinal, attrs["norm"], attrs["lang"]))
        if attested:
            affected_digests[record_id] = sha256(raw).hexdigest()
            document = parse_tt_record(
                raw, source_record_id=record_id, source_path=path,
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit=PIN, packaging=packaging,
            )
            for ordinal, original_norm, original_lang in attested:
                word = document.words[ordinal - 1]
                assert word.ordinal == ordinal
                assert word.norm == original_norm
                assert word.original_lang == original_lang, (
                    "parser lost original norm.lang literal"
                )

    assert count_documents == 2_628, "pinned source record count drift"
    assert count_norms == 2_394_354, "pinned original norm openings drift"
    assert len(expected) == 57_369, "original norm.lang source count drift"

    if native is not None:
        from tf.fabric import Fabric
        api = Fabric(locations=[str(native)], silent="deep").load(
            "source_attr_norm_lang source_record_id source_word_ordinal source_sha256 norm",
            silent="deep",
        )
        assert api, "could not reload full native Text-Fabric"
        assert api.F.otype.maxSlot == count_norms
        assert len(api.F.otype.s("document")) == count_documents
        matched = set()
        for slot in range(1, count_norms + 1):
            key = (api.F.source_record_id.v(slot),
                   api.F.source_word_ordinal.v(slot))
            literal = api.F.source_attr_norm_lang.v(slot)
            original = expected.get(key)
            if original is None:
                assert literal is None, "native invented absent original norm.lang"
            else:
                norm, lang = original
                assert literal == lang, "native original norm.lang value mismatch"
                assert api.F.norm.v(slot) == norm, "native original norm changed"
                matched.add(key)
        assert matched == set(expected), "native original norm.lang labels missing"
        for record_id, digest in affected_digests.items():
            document = api.T.nodeFromSection((record_id,))
            assert document is not None, "source section missing"
            assert api.F.source_sha256.v(document) == digest, (
                "native original TT source SHA mismatch"
            )

    print("PASS pinned norm.lang source-to-native parity",
          f"original_records={count_documents}",
          f"original_word_slots={count_norms}",
          f"norm_lang_attrs={len(expected)}",
          f"affected_records={len(affected_digests)}",
          f"native_reload={native is not None}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--native", type=Path)
    args = parser.parse_args()
    audit(args.upstream, args.native)
