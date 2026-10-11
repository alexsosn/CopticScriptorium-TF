"""Live exact LXX edition-variant *address* audit of pinned Coptic OT gap cases."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copticscriptorium_tf.lxx_modules import validate_lxx_release
from copticscriptorium_tf.ot_variant_probe import probe_pinned_variant_gaps

FIXTURE = ROOT / "research/issue-149/pinned-ambiguous-gaps.json"


def main(tf_dir: Path) -> None:
    api = Fabric(locations=[str(tf_dir)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    assert api, "Greek Text-Fabric 1935 parent did not load"
    validate_lxx_release(tf_dir, api)

    def lookup(book: str, chapter: int, verse: int) -> int | None:
        node = api.T.nodeFromSection((book, chapter, verse))
        if node is None:
            return None
        if api.F.otype.v(node) != "verse":
            raise ValueError(f"Greek candidate {book} {chapter}:{verse} is not verse")
        return node

    def subverse_count(node: int) -> int:
        return len(api.L.d(node, otype="subverse"))

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    reports = probe_pinned_variant_gaps(
        fixture, lookup=lookup, subverse_count=subverse_count
    )
    observed = Counter()
    by_work: dict[str, Counter] = {}
    for gap in reports:
        assert gap.status == "unresolved_edition"
        assert gap.selected_lxx_book is None
        for variant in gap.variants:
            addresses = (variant.before, *variant.intermediate, variant.after)
            counts = Counter("present" if a.node is not None else "absent" for a in addresses)
            observed.update(counts)
            by_work.setdefault(gap.source_cts_work, Counter()).update({
                f"{variant.book}_present": counts["present"],
                f"{variant.book}_absent": counts["absent"],
            })
            assert all(a.subverse_count >= 0 for a in addresses)
    assert len(reports) == 10
    assert sum(
        r.current_verse - r.previous_verse - 1 for r in reports
    ) == 50
    # Both alternatives and both flanking markers are examined: 50 intermediate
    # + 20 flanking source addresses, each checked against two Greek editions.
    assert sum(observed.values()) == 140, observed
    print(json.dumps({
        "source_evidence": "10 exact source-byte-qualified gaps from prior 2,628-record CI audit",
        "greek_parent": "CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076",
        "greek_parent_fingerprint_verified": True,
        "source_gap_events": len(reports),
        "source_gap_intermediate_numbers": 50,
        "variant_address_probes": dict(sorted(observed.items())),
        "per_work_variant_address_probes": {
            work: dict(sorted(counts.items()))
            for work, counts in sorted(by_work.items())
        },
        "statuses": ["unresolved_edition"],
        "interpretation": (
            "Greek address existence only. Neither Greek book variant is selected; "
            "no bilingual passage, textual omission or word alignment asserted."
        ),
    }, sort_keys=True))
    print("PASS ten Coptic OT edition-ambiguous gaps, both Greek variants checked, no guessed alignment")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue149_variants.py /path/to/lxx/tf/1935")
    main(Path(sys.argv[1]))
