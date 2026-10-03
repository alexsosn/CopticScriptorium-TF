"""RED-first local Text-Fabric web-app contract for issue #58."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml
from tf.app import use
from tf.browser.web import setup as setup_browser

from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.model import (
    DocumentModel,
    Entity,
    NormGroup,
    Orig,
    Sentence,
    Translation,
    Word,
)
from copticscriptorium_tf.writer import write_graph


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
APP_CONFIG = APP_DIR / "config.yaml"


def _document(record: str, *, expanded: bool) -> DocumentModel:
    corpus, name = record.split(":", 1)
    dataset = f"{corpus}/{corpus}"
    scholarly = "urn:cts:copticLit:fixture.shared"
    words = (
        Word(1, "w1", "ⲁ", "lemma1", "N", "root", None, 0, "ab"),
        Word(2, "w2", "ⲃ", "lemma2", "V", "dep", "#w1", 1, "cd"),
    ) if expanded else (
        Word(1, "w1", "ⲅ", "lemma3", "N", "root", None, 0, "ef"),
    )
    metadata = {
        "title": name,
        "document_cts_urn": scholarly,
        "license": "fixture",
    }
    if expanded:
        metadata["witness"] = f"cf. {scholarly}"
    return DocumentModel(
        source_record_id=f"{dataset}:{name}",
        source_path=f"{corpus}/{corpus}_TT/{name}.tt",
        source_sha256=("a" if expanded else "b") * 64,
        packaging="directory",
        upstream_repository="fixture/repo",
        upstream_commit="a" * 40,
        corpus=corpus,
        dataset=dataset,
        record=name,
        scholarly_id=scholarly,
        metadata=metadata,
        metadata_duplicates={},
        words=words,
        sentences=(Sentence(1, tuple(range(1, len(words) + 1))),),
        origs=(Orig("ab", (1,), 0),) if expanded else (),
        norm_groups=(NormGroup("ab-cd", (0,), (2,), None),) if expanded else (),
        orig_groups=(),
        layout_events=(),
        entities=(Entity(1, None, "person", "Q123", "#w2", 2, (1, 2)),)
        if expanded else (),
        translations=(Translation(1, "English translation", (1, 2)),)
        if expanded else (),
        arabic_translations=(Translation(1, "ترجمة عربية", (1,)),)
        if expanded else (),
        source_text="fixture",
    )


def _graph():
    return build_graph(
        (
            _document("beta:b", expanded=False),
            _document("alpha:a", expanded=True),
        )
    )


class WebAppContractTests(unittest.TestCase):
    def test_app_is_config_only_and_declares_local_research_defaults(self):
        self.assertTrue(APP_CONFIG.is_file(), "issue #58 requires app/config.yaml")
        self.assertFalse((APP_DIR / "app.py").exists(), "custom app hooks are not needed")

        config = yaml.safe_load(APP_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["apiVersion"], 3)
        self.assertEqual(config["dataDisplay"]["browseNavLevel"], 0)
        self.assertEqual(config["dataDisplay"]["textFormat"], "text-orig-full")
        self.assertIsNone(config["provenanceSpec"]["org"])
        self.assertIsNone(config["provenanceSpec"]["repo"])
        self.assertEqual(config["provenanceSpec"]["relative"], ".")
        self.assertNotIn("writing", config)
        self.assertTrue(config["interfaceDefaults"]["withNodes"])
        self.assertTrue(config["interfaceDefaults"]["withTypes"])
        self.assertTrue(config["interfaceDefaults"]["standardFeatures"])
        self.assertTrue(config["interfaceDefaults"]["queryFeatures"])
        self.assertTrue(config["interfaceDefaults"]["multiFeatures"])

        # Optional node types and optional annotation features must not be named in
        # static app configuration: small valid corpora may not contain them.
        self.assertEqual(set(config["typeDisplay"]), {"document", "word"})
        word_display = config["typeDisplay"]["word"]
        for feature in ("source_record_id", "source_word_ordinal"):
            self.assertIn(feature, word_display["features"].split())
        document_display = config["typeDisplay"]["document"]
        for feature in (
            "source_record_id",
            "corpus",
            "dataset",
            "source_path",
            "source_sha256",
            "packaging",
        ):
            self.assertIn(feature, document_display["features"].split())

    def test_generated_tf_loads_through_app_searches_and_renders_both_text_modes(self):
        graph = _graph()
        with TemporaryDirectory() as temporary:
            location = write_graph(graph, Path(temporary) / "tf")
            app = use(
                f"app:{APP_DIR}",
                locations=[str(location)],
                modules=["."],
                silent="deep",
            )
            self.assertIsNotNone(app)
            self.assertIsNotNone(app.api)
            api = app.api

            document = next(
                node
                for node in graph.nodes
                if node.otype == "document" and node.corpus == "alpha"
            )
            self.assertEqual(
                api.T.nodeFromSection((document.source_record_id,)), document.id
            )
            self.assertEqual(app.context.textFormat, "text-orig-full")
            normalized = api.T.text(document.id, fmt="text-orig-full")
            diplomatic = api.T.text(document.id, fmt="text-diplomatic-full")
            self.assertEqual(normalized, "ⲁ ⲃ ")
            self.assertNotEqual(diplomatic, normalized)

            results = app.search("word lemma=lemma2", silent="deep")
            self.assertEqual(results, [(2,)])
            self.assertEqual(api.F.pos.v(2), "V")
            self.assertTrue(tuple(api.E.dependency_head.f(2)))

            entity = next(node for node in graph.nodes if node.otype == "entity")
            translation = next(
                node for node in graph.nodes if node.otype == "translation"
            )
            arabic = next(
                node for node in graph.nodes if node.otype == "arabic_translation"
            )
            self.assertEqual(api.F.entity_class.v(entity.id), "person")
            self.assertTrue(tuple(api.E.entity_head.f(entity.id)))
            self.assertEqual(api.T.text(translation.id), "English translation")
            self.assertEqual(api.T.text(arabic.id), "ترجمة عربية")

            documents = [node for node in graph.nodes if node.otype == "document"]
            self.assertTrue(
                any(tuple(api.E.same_scholarly.f(node.id)) for node in documents)
            )
            self.assertTrue(
                any(tuple(api.E.witness.f(node.id)) for node in documents)
            )

            vanilla = __import__("tf.fabric", fromlist=["Fabric"]).Fabric(
                locations=[str(location)], silent="deep"
            ).load("lemma pos", silent="deep")
            self.assertTrue(vanilla)

    def test_standard_browser_constructs_and_serves_query_route(self):
        graph = _graph()
        with TemporaryDirectory() as temporary:
            location = write_graph(graph, Path(temporary) / "tf")
            browser = setup_browser(
                False,
                f"app:{APP_DIR}",
                f"--locations={location}",
                "--modules=.",
            )
            self.assertIsNotNone(browser)
            routes = {rule.rule for rule in browser.url_map.iter_rules()}
            self.assertIn("/query", routes)
            response = browser.test_client().get("/query")
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
