"""Native Text-Fabric regression contract for issue #15.

These tests intentionally reject serialized JSON/XML containers in semantic TF
features. Upstream literal strings may contain markup; structural data may not be
hidden inside such strings.
"""
from __future__ import annotations

from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric

from copticscriptorium_tf.graph import DocumentRelation, build_graph
from copticscriptorium_tf.model import DocumentModel, NormGroup, Sentence, Word
from copticscriptorium_tf import writer


def _document(
    source_record_id: str,
    *,
    title: str,
    scholarly_id: str,
    expanded: bool,
) -> DocumentModel:
    prefix, record = source_record_id.split(":", 1)
    corpus, dataset = prefix.split("/", 1)
    words = (
        Word(1, "w1", "ⲁ", "lemma1", "N", "root", None, 0, "a"),
        Word(2, "w2", "ⲃ", "lemma2", "V", "dep", "#w1", 1, "b"),
    ) if expanded else (
        Word(1, "w1", "ⲅ", "lemma3", "N", "root", None, 0, "c"),
    )
    metadata = {
        "title": title,
        "title__2": "literal source key using occurrence-like suffix",
        "document_cts_urn": scholarly_id,
        "license": "literal <a href='https://example.invalid/'>source markup</a>",
        "odd-key": "unsafe feature-name key",
    }
    return DocumentModel(
        source_record_id=source_record_id,
        source_path=f"{corpus}/{dataset}_TT/{record}.tt",
        source_sha256=("a" if expanded else "b") * 64,
        packaging="directory",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit="3ac067f1709a0012daf39ea8da2fac79980176a5",
        corpus=corpus,
        dataset=f"{corpus}/{dataset}",
        record=record,
        scholarly_id=scholarly_id,
        metadata=metadata,
        metadata_duplicates={"title": (title, f"{title} duplicate")} if expanded else {},
        words=words,
        sentences=(Sentence(1, tuple(range(1, len(words) + 1))),),
        origs=(),
        norm_groups=(NormGroup("ab", (), (1, 2), None),) if expanded else (),
        orig_groups=(),
        layout_events=(),
        entities=(),
        translations=(),
        arabic_translations=(),
        source_text="fixture",
    )


def _graph():
    scholarly = "urn:cts:copticLit:fixture.same"
    source = _document("alpha/sample:a", title="Alpha", scholarly_id=scholarly, expanded=True)
    target = _document("beta/sample:b", title="Beta", scholarly_id=scholarly, expanded=False)
    return build_graph(
        (source, target),
        document_relations=(
            DocumentRelation(
                "same_scholarly",
                source.source_record_id,
                target.source_record_id,
                classification="alternate_analysis",
            ),
            DocumentRelation(
                "documented_overlap",
                source.source_record_id,
                target.source_record_id,
                classification="textual_divergence",
                family="fixture-family",
            ),
            DocumentRelation(
                "witness",
                source.source_record_id,
                target.source_record_id,
                witness_literal="cf. urn:cts:copticLit:fixture.same",
                target_scholarly_id=scholarly,
            ),
        ),
    )


def _reload(location: Path):
    api = Fabric(locations=[str(location)], silent="deep").load(
        "meta_title meta_title__2 meta__hex_7469746c655f5f32 "
        "meta_document_cts_urn meta_license meta__hex_6f64642d6b6579 "
        "direct_word dependency_head same_scholarly same_scholarly_classification "
        "documented_overlap documented_overlap_classification documented_overlap_family "
        "witness witness_literal witness_target_scholarly_id",
        silent="deep",
    )
    if api is False or api is None:
        raise AssertionError("fresh Text-Fabric reload failed")
    return api


class NativeTfProjectionTests(unittest.TestCase):
    def test_metadata_feature_name_encoding_is_tf_safe_and_collision_free(self):
        self.assertEqual(writer._metadata_feature_name("title"), "meta_title")
        self.assertEqual(writer._metadata_feature_name("document_cts_urn"), "meta_document_cts_urn")
        self.assertEqual(writer._metadata_feature_name("odd-key"), "meta__hex_6f64642d6b6579")
        self.assertEqual(writer._metadata_feature_name("title__2"), "meta__hex_7469746c655f5f32")
        self.assertNotEqual(writer._metadata_feature_name("title__2"), "meta_title__2")
        names = {
            writer._metadata_feature_name("odd-key"),
            writer._metadata_feature_name("_hex_6f64642d6b6579"),
            writer._metadata_feature_name("odd_key"),
            writer._metadata_feature_name("title__2"),
        }
        self.assertEqual(len(names), 4)
        self.assertTrue(all(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) for name in names))

    def test_saved_feature_inventory_has_no_structural_json_features(self):
        with TemporaryDirectory() as temporary:
            location = writer.write_graph(_graph(), Path(temporary) / "corpus")
            feature_names = {path.stem for path in location.glob("*.tf")}
            self.assertFalse({name for name in feature_names if name.endswith("_json")})
            self.assertNotIn("metadata_json", feature_names)
            self.assertNotIn("metadata_duplicates_json", feature_names)
            self.assertNotIn("direct_word_slots_json", feature_names)
            self.assertNotIn("section_address_json", feature_names)

    def test_metadata_duplicates_and_literal_markup_are_native_scalar_features(self):
        graph = _graph()
        with TemporaryDirectory() as temporary:
            api = _reload(writer.write_graph(graph, Path(temporary) / "corpus"))
            source = next(node for node in graph.nodes if node.otype == "document" and node.corpus == "alpha")
            self.assertEqual(api.F.meta_title.v(source.id), "Alpha")
            self.assertEqual(api.F.meta_title__2.v(source.id), "Alpha duplicate")
            self.assertEqual(
                api.F.meta__hex_7469746c655f5f32.v(source.id),
                "literal source key using occurrence-like suffix",
            )
            self.assertEqual(api.F.meta_document_cts_urn.v(source.id), source.scholarly_id)
            self.assertEqual(
                api.F.meta_license.v(source.id),
                "literal <a href='https://example.invalid/'>source markup</a>",
            )
            self.assertEqual(api.F.meta__hex_6f64642d6b6579.v(source.id), "unsafe feature-name key")

    def test_direct_word_membership_is_a_native_edge(self):
        graph = _graph()
        with TemporaryDirectory() as temporary:
            api = _reload(writer.write_graph(graph, Path(temporary) / "corpus"))
            group = next(node for node in graph.nodes if node.otype == "norm_group")
            self.assertEqual(tuple(api.E.direct_word.f(group.id)), group.direct_word_slots)

    def test_document_relation_evidence_is_split_into_native_edge_features(self):
        graph = _graph()
        with TemporaryDirectory() as temporary:
            api = _reload(writer.write_graph(graph, Path(temporary) / "corpus"))
            for edge in graph.edges:
                if edge.kind == "same_scholarly":
                    self.assertIn(edge.target, api.E.same_scholarly.f(edge.source))
                    self.assertEqual(
                        dict(api.E.same_scholarly_classification.f(edge.source))[edge.target],
                        edge.classification,
                    )
                elif edge.kind == "documented_overlap":
                    self.assertIn(edge.target, api.E.documented_overlap.f(edge.source))
                    self.assertEqual(
                        dict(api.E.documented_overlap_classification.f(edge.source))[edge.target],
                        edge.classification,
                    )
                    self.assertEqual(
                        dict(api.E.documented_overlap_family.f(edge.source))[edge.target],
                        edge.family,
                    )
                elif edge.kind == "witness":
                    self.assertIn(edge.target, api.E.witness.f(edge.source))
                    self.assertEqual(
                        dict(api.E.witness_literal.f(edge.source))[edge.target],
                        edge.witness_literal,
                    )
                    self.assertEqual(
                        dict(api.E.witness_target_scholarly_id.f(edge.source))[edge.target],
                        edge.target_scholarly_id,
                    )


if __name__ == "__main__":
    unittest.main()
