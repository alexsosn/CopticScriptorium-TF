"""#143 independent sample raw TT opening counts and parser source occurrences."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

from copticscriptorium_tf.parser import parse_tt_record

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
FILES = (
    "AP/apophthegmata.patrum_TT/AP.001.n135.mother.tt",
    "pistis-sophia/pistis.sophia_TT/pistis.sophia_Postscript_part1.tt",
    "bohairic-lausiac/bohairic.lausiac_TT/bohairic.lausiac_01.tt",
)


def main(root: Path) -> None:
    for rel in FILES:
        raw = (root / rel).read_bytes()
        corpus, dataset_dir, filename = rel.split("/")
        doc = parse_tt_record(
            raw,
            source_record_id=f"{corpus}/{dataset_dir.removesuffix('_TT')}:{filename.removesuffix('.tt')}",
            source_path=rel,
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        independently_counted = len(re.findall(rb"<multiword\b", raw))
        observed = doc.multiword_annotations
        assert len(observed) == independently_counted, (rel, len(observed), independently_counted)
        assert [x.ordinal for x in observed] == list(range(1, len(observed) + 1))
        print(f"PASS original TT multiword occurrence parity {rel}: {len(observed)}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue143_source_examples.py PINNED_TT")
    main(Path(sys.argv[1]))
