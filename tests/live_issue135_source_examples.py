"""Independent two-file raw TT <-> parsed positional event parity (#135)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

from copticscriptorium_tf.parser import parse_tt_record

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS = ("morph", "norm_func", "norm_head", "norm_xml:id", "norm_new_sent")
FILES = (
    "AP/apophthegmata.patrum_TT/AP.001.n135.mother.tt",
    "proclus-homilies/proclus.homilies_TT/proclus.23.nativity.tt",
)


def main(source_root: Path) -> None:
    for source_path in FILES:
        raw = (source_root / source_path).read_bytes()
        source_text = raw.decode("utf-8")
        # Independent source opening-tag count: no dependency on parse_tt_record
        # or graph event generation, and intentionally no lexical text exported.
        count = Counter({
            tag: len(re.findall(r"<" + re.escape(tag) + r"\s", source_text))
            for tag in KINDS
        })
        corpus, dataset_dir, filename = source_path.split("/")
        dataset = dataset_dir.removesuffix("_TT")
        record = filename.removesuffix(".tt")
        parsed = parse_tt_record(
            raw,
            source_record_id=f"{corpus}/{dataset}:{record}",
            source_path=source_path,
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        observed = Counter(item.kind for item in parsed.token_annotations)
        assert observed == +count, (source_path, observed, count)
        assert [item.ordinal for item in parsed.token_annotations] == list(
            range(1, len(parsed.token_annotations) + 1)
        )
        assert all(item.value is not None and
                   item.start_word_ordinal == item.end_word_ordinal
                   for item in parsed.token_annotations)
        print(f"PASS independent raw->source token wrapper count {source_path}: {dict(observed)}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue135_source_examples.py SOURCE_ROOT")
    main(Path(sys.argv[1]))
