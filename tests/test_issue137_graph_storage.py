"""RED-first graph storage measurement contract; no corpus fields in report."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from copticscriptorium_tf._graph_core import (
    Graph, GraphEdge, GraphNode, GraphSlot, NodeRange,
)
from copticscriptorium_tf.graph_storage import graph_storage_census
from copticscriptorium_tf.converter import convert_source_tree


REVISION = "a" * 40
RAW = ('<meta corpus="test" title="PRIVATE_COPTIC_SOURCE_TITLE">'
       '<norm_group norm_group="ⲁ"><norm xml:id="u1" new_sent="true" '
       'norm="ⲁ">ⲁ</norm></norm_group>'
       '<norm_group norm_group="ⲃ"><norm xml:id="u2" norm="ⲃ">ⲃ'
       '</norm></norm_group>')


def fixture_graph():
    return Graph(
        upstream_repository="fixture/private-corpus",
        upstream_commit=REVISION,
        section_types=("document",),
        slots=(
            GraphSlot(1, "private/corpus:PRIVATE_RECID", 1, "u1",
                      "PRIVATE_GREEK_WORD", None, None, None, None,
                      None, "PRIVATE_SURFACE"),
            GraphSlot(2, "private/corpus:PRIVATE_RECID", 2, "u2",
                      "PRIVATE_COPTIC_WORD", None, None, None, None,
                      None, "PRIVATE_SURFACE_2"),
        ),
        nodes=(
            GraphNode(3, "document", "private/corpus:PRIVATE_RECID", 1,
                      ((1, 2),), text="PRIVATE_NODE_VALUE"),
            GraphNode(4, "sbl_greek", "private/corpus:PRIVATE_RECID", 2,
                      ((1, 1), (2, 2)), value="PRIVATE_GREEK_ANNOTATION"),
        ),
        edges=(
            GraphEdge("direct_word", 3, 1),
            GraphEdge("direct_word", 3, 2),
            GraphEdge("witness_literal", 3, 4, witness_literal="PRIVATE_WITNESS"),
        ),
        node_ranges=(NodeRange("document", 3, 3, 1),
                     NodeRange("sbl_greek", 4, 4, 1)),
    )


class GraphStorageCensusTests(unittest.TestCase):
    def test_counts_source_free_object_and_locus_shapes(self):
        a = graph_storage_census(fixture_graph())
        self.assertEqual(a["graph_slots"], 2)
        self.assertEqual(a["graph_nodes"], 2)
        self.assertEqual(a["graph_edges"], 3)
        self.assertEqual(a["node_types"], {"document": 1, "sbl_greek": 1})
        self.assertEqual(a["edge_types"], {"direct_word": 2, "witness_literal": 1})
        self.assertEqual(a["range_segments"], 3)
        self.assertEqual(a["range_cardinality"]["single_segment"], 1)
        self.assertEqual(a["range_cardinality"]["multiple_segments"], 1)
        self.assertEqual(a["range_cardinality"]["empty"], 0)
        self.assertEqual(a["range_covered_slot_occurrences"], 4)
        self.assertGreater(a["shallow_bytes"]["graph_node_objects"], 0)
        self.assertGreater(a["shallow_bytes"]["node_range_containers"], 0)
        self.assertGreater(a["shallow_bytes"]["node_range_segment_tuples"], 0)
        self.assertIn("not", a["measurement_limitation"].lower())
        serialized = json.dumps(a, ensure_ascii=False)
        for forbidden in (
            "PRIVATE_", "fixture/private-corpus", "ⲁ", "ⲃ",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_empty_and_invalid_locus_types_are_categorized_or_rejected(self):
        graph = fixture_graph()
        empty = GraphNode(5, "lang", "private/corpus:PRIVATE_RECID", 3, ())
        graph = Graph(
            graph.upstream_repository, graph.upstream_commit,
            graph.section_types, graph.slots, graph.nodes + (empty,),
            graph.edges, graph.node_ranges,
        )
        self.assertEqual(graph_storage_census(graph)["range_cardinality"]["empty"], 1)
        bad = GraphNode(6, "sbl_apparatus", "private/corpus:PRIVATE_RECID",
                        4, ((3, 2),))
        graph = Graph(
            graph.upstream_repository, graph.upstream_commit,
            graph.section_types, graph.slots, graph.nodes + (bad,),
            graph.edges, graph.node_ranges,
        )
        with self.assertRaisesRegex(ValueError, "range"):
            graph_storage_census(graph)

    def test_opt_in_converter_probe_does_not_change_native_tf_bytes(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            folder = source / "test" / "test_TT"
            folder.mkdir(parents=True)
            (folder / "sample.tt").write_text(RAW, encoding="utf-8")
            baseline = root / "base"
            measured = root / "measured"
            normal = convert_source_tree(
                source, baseline, upstream_repository="fixture/repo",
                upstream_commit=REVISION,
            )
            profiles = []

            def measure(graph):
                profiles.append(graph_storage_census(graph))

            probed = convert_source_tree(
                source, measured, upstream_repository="fixture/repo",
                upstream_commit=REVISION, graph_probe=measure,
            )
            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0]["graph_slots"], normal.slots)
            self.assertEqual(profiles[0]["graph_nodes"], normal.nodes)
            self.assertEqual(profiles[0]["graph_edges"], normal.edges)
            self.assertEqual((normal.slots, normal.nodes, normal.edges),
                             (probed.slots, probed.nodes, probed.edges))
            files_base = {p.name: sha256(p.read_bytes()).hexdigest()
                          for p in baseline.glob("*.tf")}
            files_measured = {p.name: sha256(p.read_bytes()).hexdigest()
                              for p in measured.glob("*.tf")}
            self.assertEqual(files_base, files_measured)
            self.assertFalse(any(name.endswith("_json.tf")
                                 for name in files_measured))


if __name__ == "__main__":
    unittest.main()
