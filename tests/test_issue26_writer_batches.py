"""RED contract for issue #26 incremental Text-Fabric projection/save."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tf.fabric import Fabric

from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.model import DocumentModel, NormGroup, Sentence, Word
from copticscriptorium_tf import writer


def _graph():
    words = (
        Word(1, "w1", "ⲁ", "lemma1", "N", "root", None, 0, "a"),
        Word(2, "w2", "ⲃ", "lemma2", "V", "dep", "#w1", 1, "b"),
    )
    document = DocumentModel(
        source_record_id="demo/demo:one",
        source_path="demo/demo_TT/one.tt",
        source_sha256="a" * 64,
        packaging="directory",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit="3ac067f1709a0012daf39ea8da2fac79980176a5",
        corpus="demo",
        dataset="demo/demo",
        record="one",
        scholarly_id="urn:cts:copticLit:demo.one",
        metadata={"title": "One", "license": "fixture"},
        metadata_duplicates={},
        words=words,
        sentences=(Sentence(1, (1, 2)),),
        origs=(),
        norm_groups=(NormGroup("ab", (), (1, 2), None),),
        orig_groups=(),
        layout_events=(),
        entities=(),
        translations=(),
        arabic_translations=(),
        source_text="fixture",
    )
    return build_graph((document,))


class IncrementalWriterMemoryContractTests(unittest.TestCase):
    def test_write_graph_saves_bounded_feature_batches_without_monolithic_projection(self) -> None:
        graph = _graph()
        calls: list[tuple[set[str], set[str], set[str]]] = []
        original_save = Fabric.save

        def recording_save(fabric, *args, **kwargs):
            node_features = kwargs.get("nodeFeatures", {})
            edge_features = kwargs.get("edgeFeatures", {})
            metadata = kwargs.get("metaData", {})
            calls.append((set(node_features), set(edge_features), set(metadata)))
            return original_save(fabric, *args, **kwargs)

        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "tf"
            with (
                patch.object(Fabric, "save", new=recording_save),
                patch.object(
                    writer,
                    "_project",
                    create=True,
                    side_effect=AssertionError("write_graph materialized the monolithic projection"),
                ),
            ):
                writer.write_graph(graph, destination)

        self.assertGreater(len(calls), 3)
        first_nodes, first_edges, first_meta = calls[0]
        self.assertEqual(first_nodes, {"otype"})
        self.assertEqual(first_edges, {"oslots"})
        self.assertIn("", first_meta)

        data_feature_names: set[str] = set()
        saw_otext = False
        for node_names, edge_names, metadata_names in calls:
            self.assertLessEqual(
                len(node_names) + len(edge_names),
                2,
                "one save batch retained too many feature maps at once",
            )
            self.assertIn("", metadata_names)
            data_feature_names.update(node_names)
            data_feature_names.update(edge_names)
            saw_otext = saw_otext or "otext" in metadata_names

        self.assertIn("otype", data_feature_names)
        self.assertIn("oslots", data_feature_names)
        self.assertIn("norm", data_feature_names)
        self.assertIn("source_record_id", data_feature_names)
        self.assertIn("dependency_head", data_feature_names)
        self.assertIn("direct_word", data_feature_names)
        self.assertTrue(saw_otext)


if __name__ == "__main__":
    unittest.main()
