import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_graph_contract", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph contract module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_graph():
    return {
        "slots": [
            {"id": 1, "kind": "word", "surface": "ⲁⲃ", "source_word_id": "u1"},
            {"id": 2, "kind": "synthetic", "surface": "", "source_word_id": None},
            {"id": 3, "kind": "word", "surface": "ⲅ", "source_word_id": "u2"},
            {"id": 4, "kind": "word", "surface": "ⲅ", "source_word_id": "u2"},
        ],
        "nodes": [
            {
                "id": 10,
                "type": "document",
                "slots": [1, 2, 3],
                "features": {
                    "source_record_id": "demo/demo:one",
                    "corpus": "demo",
                    "dataset": "demo",
                    "scholarly_id": "urn:cts:demo:one",
                    "section_address": ["demo/demo:one"],
                    "render_mode": "normalized_slots",
                },
            },
            {
                "id": 11,
                "type": "sentence",
                "slots": [1],
                "features": {"ordinal": 1, "render_mode": "normalized_slots"},
            },
            {
                "id": 12,
                "type": "sentence",
                "slots": [3],
                "features": {"ordinal": 2, "render_mode": "normalized_slots"},
            },
            {
                "id": 20,
                "type": "line",
                "slots": [1, 3],
                "features": {
                    "diplomatic_text": "ⲁ|ⲃⲅ",
                    "start_char": 1,
                    "end_char": 1,
                    "has_internal_boundary": True,
                    "render_mode": "own_text",
                },
            },
            {
                "id": 21,
                "type": "translation",
                "slots": [2],
                "features": {
                    "text": "independently positioned translation",
                    "zero_span": True,
                    "render_mode": "own_text",
                    "after_source_word_ordinal": 1,
                },
            },
            {
                "id": 22,
                "type": "entity",
                "slots": [1, 3],
                "features": {
                    "entity_class": "person",
                    "identity": "Person A",
                    "render_mode": "normalized_slots",
                },
            },
            {
                "id": 23,
                "type": "provenance",
                "slots": [1],
                "features": {"render_mode": "none", "technical_anchor": True},
            },
            {
                "id": 24,
                "type": "document",
                "slots": [4],
                "features": {
                    "source_record_id": "copy/copy:one",
                    "corpus": "copy",
                    "dataset": "copy",
                    "scholarly_id": "urn:cts:demo:one",
                    "section_address": ["copy/copy:one"],
                    "render_mode": "normalized_slots",
                },
            },
            {
                "id": 25,
                "type": "sentence",
                "slots": [4],
                "features": {"ordinal": 1, "render_mode": "normalized_slots"},
            },
        ],
        "edges": [
            {"type": "dependency_head", "from": 3, "to": 1},
            {"type": "entity_head", "from": 22, "to": 1},
            {
                "type": "same_scholarly",
                "from": 10,
                "to": 24,
                "features": {"classification": "byte_identical"},
            },
        ],
        "section_types": ["document"],
    }


class GraphContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_module()

    def test_valid_contract_accepts_word_slots_layout_offsets_and_repeated_scholarly_id(self):
        graph = valid_graph()
        self.assertEqual(self.contract.validate_graph(graph), [])

    def test_zero_span_textual_node_requires_surface_less_synthetic_slot(self):
        graph = valid_graph()
        translation = next(node for node in graph["nodes"] if node["type"] == "translation")
        translation["slots"] = [1]
        errors = self.contract.validate_graph(graph)
        self.assertTrue(any("zero-span textual" in error for error in errors))

        graph = valid_graph()
        synthetic = next(slot for slot in graph["slots"] if slot["kind"] == "synthetic")
        synthetic["surface"] = "fabricated"
        errors = self.contract.validate_graph(graph)
        self.assertTrue(any("synthetic slot" in error for error in errors))

    def test_layout_crossing_requires_own_text_and_token_relative_offsets(self):
        graph = valid_graph()
        line = next(node for node in graph["nodes"] if node["type"] == "line")
        del line["features"]["diplomatic_text"]
        del line["features"]["start_char"]
        errors = self.contract.validate_graph(graph)
        self.assertTrue(any("layout" in error and "own text" in error for error in errors))
        self.assertTrue(any("layout" in error and "offset" in error for error in errors))

    def test_dependency_and_entity_head_edges_target_word_slots(self):
        graph = valid_graph()
        dependency = next(edge for edge in graph["edges"] if edge["type"] == "dependency_head")
        dependency["to"] = 2
        entity_head = next(edge for edge in graph["edges"] if edge["type"] == "entity_head")
        entity_head["to"] = 3
        entity = next(node for node in graph["nodes"] if node["type"] == "entity")
        entity["slots"] = [1]
        errors = self.contract.validate_graph(graph)
        self.assertTrue(any("dependency_head" in error and "word slot" in error for error in errors))
        self.assertTrue(any("entity_head" in error and "entity span" in error for error in errors))

    def test_document_section_addresses_are_unique_but_scholarly_ids_may_repeat(self):
        graph = valid_graph()
        documents = [node for node in graph["nodes"] if node["type"] == "document"]
        documents[1]["features"]["section_address"] = ["demo/demo:one"]
        errors = self.contract.validate_graph(graph)
        self.assertTrue(any("section address" in error for error in errors))
        self.assertFalse(any("scholarly_id" in error for error in errors))

    def test_sentence_is_not_a_universal_section_level(self):
        graph = valid_graph()
        graph["section_types"] = ["document", "sentence"]
        errors = self.contract.validate_graph(graph)
        self.assertTrue(any("document-only" in error for error in errors))

    def test_technical_anchor_cannot_render_anchor_slot_text(self):
        graph = valid_graph()
        provenance = next(node for node in graph["nodes"] if node["type"] == "provenance")
        provenance["features"]["render_mode"] = "normalized_slots"
        errors = self.contract.validate_graph(graph)
        self.assertTrue(any("technical anchor" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
