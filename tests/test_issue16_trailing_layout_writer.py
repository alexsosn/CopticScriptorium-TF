"""Regression for a valid zero-width layout marker after the final source word."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric

from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.writer import write_graph


class TrailingLayoutWriterTests(unittest.TestCase):
    def test_trailing_marker_reloads_without_rendering_anchor_word_text(self):
        document = parse_tt_record(
            (
                '<meta corpus="demo">\n'
                '<norm_group norm_group="ab">'
                '<norm xml:id="u1" new_sent="true" func="root" norm="ab">ab</norm>'
                '</norm_group>\n'
                '<lb_n lb_n="tail">\n'
            ).encode("utf-8"),
            source_record_id="demo/demo:one",
            source_path="demo/demo_TT/one.tt",
            upstream_repository="fixture/repo",
            upstream_commit="deadbeef",
        )
        graph = build_graph([document])
        line = next(node for node in graph.nodes if node.otype == "line")
        self.assertEqual(line.text, "")
        self.assertEqual(line.slots, (1,))

        with TemporaryDirectory() as temporary:
            location = write_graph(graph, Path(temporary) / "tf")
            api = Fabric(locations=[str(location)], silent="deep").load(
                "own_text start_after_word_ordinal",
                silent="deep",
            )
            self.assertIsNotNone(api)
            self.assertEqual(tuple(api.L.d(line.id, otype="word")), (1,))
            self.assertEqual(api.F.start_after_word_ordinal.v(line.id), 1)
            self.assertEqual(api.F.own_text.v(line.id), "")
            self.assertEqual(api.T.text(line.id), "")


if __name__ == "__main__":
    unittest.main()
