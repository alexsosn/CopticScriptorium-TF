"""RED-first acceptance for distinct diplomatic reconstruction and own-text nodes."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric

from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.model import NormGroup, Orig, OrigGroup
from copticscriptorium_tf.writer import write_graph
from test_issue15_writer_integration import _doc


def _reload_single(path: Path):
    # A one-document graph has no same_scholarly/witness edge files; do not
    # require fixture-specific features unrelated to diplomatic rendering.
    api = Fabric(locations=[str(path)], silent="deep").load(
        "norm source_record_id value own_text", silent="deep"
    )
    if api is False or api is None:
        raise AssertionError("single-document TF reload failed")
    return api


class DiplomaticTextTests(unittest.TestCase):
    def test_direct_norm_within_norm_group_uses_source_text_and_orig_literal(self):
        document = _doc("alpha:a", expanded=True)
        graph = build_graph((document,), document_relations=())
        with TemporaryDirectory() as temporary:
            api = _reload_single(write_graph(graph, Path(temporary) / "tf"))
            doc = next(node for node in graph.nodes if node.otype == "document")
            orig = next(node for node in graph.nodes if node.otype == "orig")
            group = next(node for node in graph.nodes if node.otype == "norm_group")
            self.assertEqual(api.T.text(doc.id, fmt="text-orig-full"), "ⲁ ⲃ ")
            self.assertEqual(api.T.text(doc.id, fmt="text-diplomatic-full"), "abcd ")
            self.assertEqual(api.T.text(orig.id), "ab")
            self.assertEqual(api.T.text(group.id), "ab-cd")
            self.assertEqual([api.T.text(n.id) for n in graph.nodes if n.otype == "line"], ["a", "b", "cd"])

    def test_multi_orig_group_prefers_authoritative_original_group_value(self):
        base = _doc("alpha:a", expanded=True)
        document = replace(
            base,
            origs=(Orig("ab", (1,), 0), Orig("cd", (2,), 0)),
            norm_groups=(NormGroup("ab-cd", (0, 1), (), 0),),
            orig_groups=(OrigGroup("source-diplomatic-group", (0,)),),
        )
        graph = build_graph((document,), document_relations=())
        with TemporaryDirectory() as temporary:
            api = _reload_single(write_graph(graph, Path(temporary) / "tf"))
            doc = next(node for node in graph.nodes if node.otype == "document")
            group = next(node for node in graph.nodes if node.otype == "orig_group")
            origs = [node for node in graph.nodes if node.otype == "orig"]
            self.assertEqual(api.T.text(doc.id, fmt="text-diplomatic-full"), "source-diplomatic-group ")
            self.assertEqual(api.T.text(group.id), "source-diplomatic-group")
            self.assertEqual([api.T.text(node.id) for node in origs], ["ab", "cd"])
            self.assertEqual(api.T.text(doc.id, fmt="text-orig-full"), "ⲁ ⲃ ")


if __name__ == "__main__":
    unittest.main()
