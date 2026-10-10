"""Real pinned Coptic source regression for native biblical reference features."""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph
from tf.fabric import Fabric

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
SOURCES = (
    ("sahidic.ruth", "sahidic.ruth", "Ruth_02.tt", 23, True),
    ("sahidic.jonah", "sahidic.jonah", "Jonah_02.tt", 11, False),
    ("bohairic-habakkuk", "bohairic.habakkuk", "bohairic.Habakkuk_02.tt", 20, False),
)


def main(upstream: Path) -> None:
    docs = []
    for corpus, dataset, filename, expected_verses, has_cts in SOURCES:
        path = f"{corpus}/{dataset}_TT/{filename}"
        document = parse_tt_record(
            (upstream / path).read_bytes(),
            source_record_id=f"{corpus}/{dataset}:{filename[:-3]}",
            source_path=path,
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=PIN,
        )
        assert document.metadata["chapter"].lstrip("0") == "2"
        verses = {word.verse_n for word in document.words if word.verse_n is not None}
        assert len(verses) == expected_verses, (path, len(verses), expected_verses)
        assert document.words[0].verse_n == "1", path
        if has_cts:
            assert any(word.vid_n for word in document.words), path
            assert any(word.verse_vid for word in document.words), path
        else:
            assert all(word.vid_n is None for word in document.words), path
            assert all(word.verse_vid is None for word in document.words), path
        docs.append(document)
    graph = build_graph(docs)
    assert len(graph.slots) == sum(len(doc.words) for doc in docs)
    with TemporaryDirectory(prefix="coptic-real-verse-") as temp:
        tf_dir = Path(temp) / "tf"
        write_graph(graph, tf_dir)
        api = Fabric(locations=[str(tf_dir)], silent="deep").load(
            "source_record_id norm verse_n vid_n verse_vid", silent="deep"
        )
        assert api
        assert api.F.otype.maxSlot == len(graph.slots)
        assert len(api.F.otype.s("document")) == 3
        for document in api.F.otype.s("document"):
            words = api.L.d(document, otype="word")
            first = words[0]
            assert api.F.verse_n.v(first) == "1"
        assert any(api.F.verse_vid.v(slot.id) == "Ruth 2:1" for slot in graph.slots)
        assert any(api.F.vid_n.v(slot.id) for slot in graph.slots)
        print(
            f"PASS 3 real pinned biblical records, {len(graph.slots)} word slots, "
            f"native verse/CTS features and source-faithful reload, Git {PIN}"
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue69_pinned_verses.py SOURCE_ROOT")
    main(Path(sys.argv[1]))
