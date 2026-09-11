import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_union_contract", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph contract module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def graph():
    return {
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
                    "source_record_id": "source/source:one",
                    "section_address": ["source/source:one"],
                    "corpus": "source",
                    "dataset": "source",
                    "scholarly_id": "urn:cts:demo:one",
                },
            },
            {
                "id": "d2",
                "type": "document",
                "slots": ["w2"],
                "features": {
                    "source_record_id": "treebank/treebank:one",
                    "section_address": ["treebank/treebank:one"],
                    "corpus": "treebank",
                    "dataset": "treebank",
                    "scholarly_id": "urn:cts:demo:one",
                },
            },
            {"id": "s1", "type": "sentence", "slots": ["w1"], "features": {"ordinal": 1}},
            {"id": "s2", "type": "sentence", "slots": ["w2"], "features": {"ordinal": 1}},
        ],
        "edges": [
            {
                "type": "same_scholarly",
                "from": "d1",
                "to": "d2",
                "features": {"classification": "byte_identical"},
            },
            {
                "type": "documented_overlap",
                "from": "d1",
                "to": "d2",
                "features": {
                    "classification": "alternate_analysis",
                    "family": "fixture",
                },
            },
            {
                "type": "witness",
                "from": "d1",
                "to": "d2",
                "features": {
                    "witness_literal": "urn:cts:demo:one",
                    "target_scholarly_id": "urn:cts:demo:one",
                },
            },
        ],
    }


class UnionDocumentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_module()

    def test_document_requires_corpus_dataset_and_source_record_section_address(self):
        candidate = graph()
        self.assertEqual(self.contract.validate_graph(candidate), [])

        candidate = graph()
        del candidate["nodes"][0]["features"]["corpus"]
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("corpus" in error and "document" in error for error in errors), errors)

        candidate = graph()
        del candidate["nodes"][0]["features"]["dataset"]
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("dataset" in error and "document" in error for error in errors), errors)

        candidate = graph()
        candidate["nodes"][0]["features"]["section_address"] = ["pretty-title"]
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("section address" in error and "source_record_id" in error for error in errors), errors)

    def test_same_scholarly_and_documented_overlap_edges_are_typed_document_relations(self):
        candidate = graph()
        self.assertEqual(self.contract.validate_graph(candidate), [])

        candidate = graph()
        candidate["edges"][0]["to"] = "w2"
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("same_scholarly" in error and "document" in error for error in errors), errors)

        candidate = graph()
        del candidate["edges"][0]["features"]["classification"]
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("same_scholarly" in error and "classification" in error for error in errors), errors)

        candidate = graph()
        candidate["edges"][1]["features"]["classification"] = "not_measured"
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("documented_overlap" in error and "classification" in error for error in errors), errors)

    def test_witness_edge_preserves_literal_evidence_and_target_scholarly_identity(self):
        candidate = graph()
        self.assertEqual(self.contract.validate_graph(candidate), [])

        candidate = graph()
        del candidate["edges"][2]["features"]["witness_literal"]
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("witness" in error and "literal" in error for error in errors), errors)

        candidate = graph()
        candidate["edges"][2]["to"] = "w2"
        errors = self.contract.validate_graph(candidate)
        self.assertTrue(any("witness" in error and "document" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
