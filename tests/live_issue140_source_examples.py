"""#140 independent edition wrapper parity from pinned real TT sources."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

from copticscriptorium_tf.parser import parse_tt_record

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS = ("ed_line_n", "ed_lb_n", "ed_page_n", "ed_pg_n")
FILES = (
    "acts-pilate/acts.pilate_TT/pilate.1643.27-28.tt",
    "shenoute-crushed/shenoute.crushed_TT/shenoute.crushed.FL125-132.tt",
    "book-bartholomew/book.bartholomew_TT/book.bartholomew_part1.tt",
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
        text = raw.decode("utf-8")
        source = Counter({
            tag: len(re.findall(r"<" + re.escape(tag) + r"\s", text))
            for tag in KINDS
        })
        nodes = Counter(event.kind for event in doc.edition_annotations)
        assert nodes == +source, (rel, nodes, source)
        assert [a.ordinal for a in doc.edition_annotations] == list(
            range(1, len(doc.edition_annotations) + 1)
        )
        assert all(isinstance(a.value, str) for a in doc.edition_annotations)
        print(f"PASS independent raw edition source count {rel}: {dict(nodes)}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue140_source_examples.py PINNED_TT")
    main(Path(sys.argv[1]))
