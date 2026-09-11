import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "issue-3" / "graph_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue3_graph_contract_arabic", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load graph contract module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def graph(arabic_slots, *, zero_span=False, include_synthetic=False):
    slots = [
        {"id": "w1", "kind": "word", "source_word_id": "u1", "surface": "ⲁ"},
    ]
    document_slots = ["w1"]
    if include_synthetic:
        slots.append({"id": "z1", "kind": "synthetic", "surface": "", "source_word_id": None})
        document_slots.append("z1")
    return {
        "provenance": {
            "upstream_repository": "CopticScriptorium/corpora",
            "upstream_commit": "abc123",
        },
        "section_types": ["document"],
        "slots": slots,
        "nodes": [
            {
                "id": "d1",
                "type": "document",
                "slots": document_slots,
                "features": {
                    "source_record_id": "demo/demo:one",
                    "section_address": ["demo/demo:one"],
                    "corpus": "demo",
                    "dataset": "demo",
                    "source_path": "demo/demo_TT/one.tt",
                    "source_sha256": "1" * 64,
                },
            },
            {"id": "s1", "type": "sentence", "slots": ["w1"], "features": {}},
            {
                "id": "a1",
                "type": "arabic_translation",
                "slots": arabic_slots,
                "features": {
                    "zero_span": zero_span,
                    "text": "بواسطة شنودة",
                    "render_mode": "own_text",
                },
            },
        ],
        "edges": [],
    }


class ArabicTranslationGraphContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_module()

    def test_arabic_translation_with_real_word_locus_is_valid(self):
        errors = self.contract.validate_graph(graph(["w1"]))
        self.assertEqual(errors, [])

    def test_zero_span_arabic_translation_requires_new_schema_gate(self):
        errors = self.contract.validate_graph(graph([], zero_span=True))
        self.assertTrue(
            any("zero-span textual node" in error and "not measured" in error for error in errors),
            errors,
        )

    def test_synthetic_slot_is_not_accepted_for_current_corpus(self):
        errors = self.contract.validate_graph(
            graph(["z1"], zero_span=True, include_synthetic=True)
        )
        self.assertTrue(
            any("synthetic slot" in error and "not measured" in error for error in errors),
            errors,
        )


if __name__ == "__main__":
    unittest.main()
