"""Live immutable Mark 2 TT → native TF source-language preservation.

Never interpret `lang=Greek` as CATSS/LXX or SBL Greek textual alignment.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
PATH = "sahidica.mark/sahidica.mark_TT/Mark_02.tt"


def verify(root: Path) -> None:
    raw = (root / PATH).read_bytes()
    doc = parse_tt_record(
        raw, source_record_id="sahidica.mark/sahidica.mark:Mark_02",
        source_path=PATH, upstream_repository="CopticScriptorium/corpora",
        upstream_commit=COPTIC_PIN,
    )
    literal_counts = Counter(a.value for a in doc.language_annotations)
    assert literal_counts == {"Greek": 61, "Hebrew": 16}, literal_counts
    assert len(doc.language_annotations) == 77
    assert len(doc.sbl_annotations) == 52
    assert Counter(a.kind for a in doc.sbl_annotations) == {
        "sbl_greek": 28, "sbl_apparatus": 24,
    }
    assert [a.ordinal for a in doc.sbl_annotations] == list(range(1, 53))
    assert [a.ordinal for a in doc.language_annotations] == list(range(1, 78))

    graph = build_graph((doc,))
    assert len(graph.slots) == len(doc.words)
    assert sum(n.otype == "lang" for n in graph.nodes) == 77
    assert sum(n.otype == "sbl_greek" for n in graph.nodes) == 28
    assert sum(n.otype == "sbl_apparatus" for n in graph.nodes) == 24

    with TemporaryDirectory(prefix="coptic-lang-tf-") as temp:
        output = Path(temp) / "tf"
        write_graph(graph, output)
        api = Fabric(locations=[str(output)], silent="deep").load(
            "value render_mode source_record_id start_word_ordinal start_char "
            "end_word_ordinal end_char", silent="deep"
        )
        assert api
        assert api.F.otype.maxSlot == len(doc.words)
        lang_nodes = api.F.otype.s("lang")
        assert len(lang_nodes) == 77
        assert Counter(api.F.value.v(n) for n in lang_nodes) == literal_counts
        for node in lang_nodes:
            assert api.F.render_mode.v(node) in {"lang_anchor", "lang_span"}
            assert len(api.L.d(node, otype="word")) >= 1
            assert api.F.source_record_id.v(node) == doc.source_record_id
        assert len(api.F.otype.s("sbl_greek")) == 28
        assert len(api.F.otype.s("sbl_apparatus")) == 24
        print(
            f"PASS real pinned Mark2 lang occurrences: Greek=61 Hebrew=16, "
            f"native TF nodes=77, SBL unchanged=28+24, Coptic slots={len(doc.words)}; "
            f"source Git={COPTIC_PIN}",
            flush=True,
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue110_real_mark_lang.py PINNED_SOURCE_ROOT")
    verify(Path(sys.argv[1]))
