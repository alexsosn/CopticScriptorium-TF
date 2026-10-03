"""RED-first researcher guide and executable cookbook contract for issue #59."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from copticscriptorium_tf.graph import DocumentRelation, build_graph
from copticscriptorium_tf.model import (
    DocumentModel,
    Entity,
    LayoutEvent,
    NormGroup,
    Orig,
    OrigGroup,
    Sentence,
    Translation,
    Word,
)
from copticscriptorium_tf.writer import write_graph


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "researcher-guide.md"
COOKBOOK = ROOT / "examples" / "query_cookbook.py"
README = ROOT / "README.md"


def _document(record: str, *, expanded: bool) -> DocumentModel:
    prefix, name = record.split(":", 1)
    corpus, dataset_name = prefix.split("/", 1)
    scholarly = "urn:cts:copticLit:fixture.shared"
    if expanded:
        words = (
            Word(1, "w1", "ⲁ", "lemma1", "N", "root", None, 0, "ab"),
            Word(2, "w2", "ⲃ", "lemma2", "V", "dep", "#w1", 1, "cd"),
        )
        metadata = {
            "title": "Alpha",
            "Title": "uppercase-title-key",
            "title__2": "literal-occurrence-looking-key",
            "document_cts_urn": scholarly,
            "license": "fixture",
            "witness": f"cf. {scholarly}",
        }
        return DocumentModel(
            source_record_id=record,
            source_path=f"{corpus}/{dataset_name}_TT/{name}.tt",
            source_sha256="a" * 64,
            packaging="directory",
            upstream_repository="fixture/repo",
            upstream_commit="b" * 40,
            corpus=corpus,
            dataset=prefix,
            record=name,
            scholarly_id=scholarly,
            metadata=metadata,
            metadata_duplicates={"title": ("Alpha", "Alpha duplicate")},
            words=words,
            sentences=(Sentence(1, (1, 2)),),
            origs=(Orig("ab", (1,), 0),),
            norm_groups=(NormGroup("ab-cd", (0,), (2,), 0),),
            orig_groups=(OrigGroup("ab-cd", (0,)),),
            layout_events=(
                LayoutEvent(1, "page", "1", None, None, 0),
                LayoutEvent(2, "column", "A", None, None, 0),
                LayoutEvent(3, "line", "1", 1, 1, 0),
                LayoutEvent(4, "line", "2", 2, 1, 1),
            ),
            entities=(
                Entity(1, None, "person", "Q123", "#w2", 2, (1, 2)),
                Entity(2, 1, "title", "Q456", "#w2", 2, (2,)),
            ),
            translations=(Translation(1, "English translation", (1, 2)),),
            arabic_translations=(Translation(1, "ترجمة عربية", (1,)),),
            source_text="fixture-alpha",
        )

    return DocumentModel(
        source_record_id=record,
        source_path=f"{corpus}/{dataset_name}_TT/{name}.tt",
        source_sha256="c" * 64,
        packaging="directory",
        upstream_repository="fixture/repo",
        upstream_commit="b" * 40,
        corpus=corpus,
        dataset=prefix,
        record=name,
        scholarly_id=scholarly,
        metadata={
            "title": "Beta",
            "document_cts_urn": scholarly,
            "license": "fixture",
        },
        metadata_duplicates={},
        words=(Word(1, "w1", "ⲅ", "lemma3", "N", "root", None, 0, "ef"),),
        sentences=(Sentence(1, (1,)),),
        origs=(),
        norm_groups=(),
        orig_groups=(),
        layout_events=(),
        entities=(),
        translations=(),
        arabic_translations=(),
        source_text="fixture-beta",
    )


def _graph():
    source = _document("alpha/sample:a", expanded=True)
    target = _document("beta/sample:b", expanded=False)
    scholarly = source.scholarly_id
    return build_graph(
        (target, source),
        document_relations=(
            DocumentRelation(
                "same_scholarly",
                source.source_record_id,
                target.source_record_id,
                classification="textual_divergence",
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
                witness_literal=f"cf. {scholarly}",
                target_scholarly_id=scholarly,
            ),
        ),
    )


def _load_cookbook():
    spec = importlib.util.spec_from_file_location("issue59_query_cookbook", COOKBOOK)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot import query cookbook")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResearcherDocumentationTests(unittest.TestCase):
    def test_guide_cookbook_and_cross_links_exist(self):
        self.assertTrue(GUIDE.is_file(), "issue #59 requires docs/researcher-guide.md")
        self.assertTrue(COOKBOOK.is_file(), "issue #59 requires examples/query_cookbook.py")

        guide = GUIDE.read_text(encoding="utf-8")
        for required in (
            "source_record_id",
            "scholarly_id",
            "dependency_head",
            "entity_head",
            "documented_overlap",
            "same_scholarly",
            "witness",
            "text-orig-full",
            "text-diplomatic-full",
            "source_sha256",
            "upstreamRepository",
            "upstreamCommit",
            "meta_",
            "direct_word",
            "start_char",
            "arabic_translation",
            "does not certify",
            "docs/web-app.md",
            "examples/query_cookbook.py",
        ):
            self.assertIn(required, guide)

        cookbook_source = COOKBOOK.read_text(encoding="utf-8")
        self.assertGreaterEqual(cookbook_source.count("S.search("), 5)
        self.assertNotIn("_json", cookbook_source)

        readme = README.read_text(encoding="utf-8")
        self.assertIn("docs/researcher-guide.md", readme)
        self.assertIn("examples/query_cookbook.py", readme)

    def test_cookbook_executes_against_fresh_generated_tf(self):
        graph = _graph()
        cookbook = _load_cookbook()

        with TemporaryDirectory() as temporary:
            location = write_graph(graph, Path(temporary) / "tf")
            api = cookbook.load_generated_tf(location)

            lemma = cookbook.lemma_hits(api, "lemma2")
            self.assertEqual(len(lemma), 1)
            self.assertEqual(api.F.source_id.v(lemma[0][0]), "w2")

            morph = cookbook.morphology_hits(api, pos="V", func="dep")
            self.assertEqual(morph, lemma)

            dependencies = cookbook.dependency_pairs(api, func="dep")
            self.assertEqual(len(dependencies), 1)
            dependent, head = dependencies[0]
            self.assertEqual(api.F.source_id.v(dependent), "w2")
            self.assertEqual(api.F.source_id.v(head), "w1")

            entities = cookbook.entity_head_occurrences(api, entity_class="person")
            self.assertEqual(len(entities), 1)
            occurrence = entities[0]
            self.assertEqual(api.F.identity.v(occurrence["entity"]), "Q123")
            self.assertEqual(api.F.source_id.v(occurrence["head"]), "w2")
            self.assertEqual(
                tuple(api.F.source_id.v(word) for word in occurrence["span"]),
                ("w1", "w2"),
            )

            translations = cookbook.translation_texts(api)
            self.assertEqual(
                [item["text"] for item in translations["translation"]],
                ["English translation"],
            )
            self.assertEqual(
                [item["text"] for item in translations["arabic_translation"]],
                ["ترجمة عربية"],
            )

            documents = cookbook.document_hits(
                api, corpus="alpha", dataset="alpha/sample"
            )
            self.assertEqual(len(documents), 1)
            alpha_document = documents[0][0]
            identity = cookbook.document_identity(api, alpha_document)
            self.assertEqual(identity["physical"], "alpha/sample:a")
            self.assertEqual(
                identity["scholarly"], "urn:cts:copticLit:fixture.shared"
            )

            same = cookbook.relation_pairs(api, "same_scholarly")
            overlap = cookbook.relation_pairs(api, "documented_overlap")
            witness = cookbook.relation_pairs(api, "witness")
            for pairs in (same, overlap, witness):
                self.assertEqual(len(pairs), 1)
                source, target = pairs[0]
                self.assertEqual(
                    (
                        api.F.source_record_id.v(source),
                        api.F.source_record_id.v(target),
                    ),
                    ("alpha/sample:a", "beta/sample:b"),
                )

            same_source, same_target = same[0]
            self.assertEqual(
                dict(api.E.same_scholarly_classification.f(same_source))[same_target],
                "textual_divergence",
            )
            overlap_source, overlap_target = overlap[0]
            self.assertEqual(
                dict(api.E.documented_overlap_classification.f(overlap_source))[
                    overlap_target
                ],
                "textual_divergence",
            )
            self.assertEqual(
                dict(api.E.documented_overlap_family.f(overlap_source))[overlap_target],
                "fixture-family",
            )
            witness_source, witness_target = witness[0]
            self.assertEqual(
                dict(api.E.witness_literal.f(witness_source))[witness_target],
                "cf. urn:cts:copticLit:fixture.shared",
            )
            self.assertEqual(
                dict(api.E.witness_target_scholarly_id.f(witness_source))[
                    witness_target
                ],
                "urn:cts:copticLit:fixture.shared",
            )

            rendered = cookbook.render_document(api, alpha_document)
            self.assertEqual(rendered["normalized"], "ⲁ ⲃ ")
            self.assertNotEqual(rendered["normalized"], rendered["diplomatic"])

            provenance = cookbook.trace_provenance(api, dependent)
            self.assertEqual(provenance["source_record_id"], "alpha/sample:a")
            self.assertTrue(provenance["source_path"].endswith("a.tt"))
            self.assertEqual(provenance["source_sha256"], "a" * 64)
            self.assertEqual(provenance["upstream_repository"], "fixture/repo")
            self.assertEqual(provenance["upstream_commit"], "b" * 40)

            document = next(
                node
                for node in graph.nodes
                if node.otype == "document"
                and node.source_record_id == "alpha/sample:a"
            )
            self.assertEqual(api.F.meta_title.v(document.id), "Alpha")
            self.assertEqual(api.F.meta_title__2.v(document.id), "Alpha duplicate")
            self.assertEqual(
                api.F.meta__hex_5469746c65.v(document.id),
                "uppercase-title-key",
            )
            self.assertEqual(
                api.F.meta__hex_7469746c655f5f32.v(document.id),
                "literal-occurrence-looking-key",
            )

            group = next(node for node in graph.nodes if node.otype == "norm_group")
            orig = next(node for node in graph.nodes if node.otype == "orig")
            self.assertEqual(tuple(api.E.parent.f(orig.id)), (group.id,))
            self.assertTrue(tuple(api.E.direct_word.f(group.id)))

            lines = [node for node in graph.nodes if node.otype == "line"]
            self.assertEqual([api.F.start_char.v(node.id) for node in lines], [1, 1])
            self.assertEqual([api.T.text(node.id) for node in lines], ["bc", "d"])


if __name__ == "__main__":
    unittest.main()
