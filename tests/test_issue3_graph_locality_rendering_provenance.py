import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_locality_contract", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph contract module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def graph():
    return {
        "provenance": {
            "upstream_repository": "CopticScriptorium/corpora",
            "upstream_commit": "abc123",
        },
        "section_types": ["document"],
        "slots": [
            {"id": "w1", "kind": "word", "surface": "ⲁ", "source_word_id": "u1"},
            {"id": "w2", "kind": "word", "surface": "ⲃ", "source_word_id": "u1"},
        ],
        "nodes": [
            {
                "id": "d1",
                "type": "document",
                "slots": ["w1"],
                "features": {
                    "source_record_id": "a/a:one",
                    "section_address": ["a/a:one"],
                    "corpus": "a",
                    "dataset": "a",
                    "source_path": "a/a_TT/one.tt",
                    "source_sha256": "1" * 64,
                },
            },
            {
                "id": "d2",
                "type": "document",
                "slots": ["w2"],
                "features": {
                    "source_record_id": "b/b:one",
                    "section_address": ["b/b:one"],
                    "corpus": "b",
                    "dataset": "b",
                    "source_path": "b/b_TT/one.tt",
                    "source_sha256": "2" * 64,
                },
            },
            {"id": "s1", "type": "sentence", "slots": ["w1"], "features": {"ordinal": 1}},
            {"id": "s2", "type": "sentence", "slots": ["w2"], "features": {"ordinal": 1}},
            {
                "id": "line1",
                "type": "line",
                "slots": ["w1"],
                "features": {"diplomatic_text": "ⲁ", "render_mode": "own_text"},
            },
            {
                "id": "t1",
                "type": "translation",
                "slots": ["w1"],
                "features": {"text": "A", "render_mode": "own_text"},
            },
        ],
        "edges": [],
    }


class GraphLocalityRenderingProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_module()

    def test_graph_and_document_source_provenance_are_required(self):
        candidate = graph()
        self.assertEqual(self.contract.validate_graph(candidate), [])

        candidate = graph()
        del candidate["provenance"]["upstream_commit"]
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("upstream" in error and "provenance" in error for error in errors), errors)

        candidate = graph()
        del candidate["nodes"][0]["features"]["source_path"]
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("source_path" in error and "document" in error for error in errors), errors)

        candidate = graph()
        del candidate["nodes"][0]["features"]["source_sha256"]
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("source_sha256" in error and "document" in error for error in errors), errors)

    def test_source_derived_node_and_dependency_cannot_cross_documents(self):
        candidate = graph()
        candidate["nodes"][2]["slots"] = ["w1", "w2"]
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("sentence" in error and "physical document" in error for error in errors), errors)

        candidate = graph()
        candidate["edges"].append({"type": "dependency_head", "from": "w1", "to": "w2"})
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("dependency_head" in error and "physical document" in error for error in errors), errors)

        candidate = graph()
        candidate["nodes"][4]["slots"] = ["w1", "w2"]
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("line" in error and "physical document" in error for error in errors), errors)

    def test_layout_and_translation_nodes_render_own_text(self):
        candidate = graph()
        candidate["nodes"][4]["features"]["render_mode"] = "normalized_slots"
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("layout node" in error and "own text" in error for error in errors), errors)

        candidate = graph()
        candidate["nodes"][5]["features"]["render_mode"] = "normalized_slots"
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("translation" in error and "own text" in error for error in errors), errors)

    def test_translation_requires_measured_word_locus(self):
        candidate = graph()
        candidate["nodes"][5]["slots"] = []
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("translation" in error and "word-slot locus" in error for error in errors), errors)

    def test_new_zero_span_textual_shape_requires_schema_gate(self):
        candidate = graph()
        candidate["nodes"][5]["slots"] = []
        candidate["nodes"][5]["features"]["zero_span"] = True
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("zero-span textual node" in error and "not measured" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
