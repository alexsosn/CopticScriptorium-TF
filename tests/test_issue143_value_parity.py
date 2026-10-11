"""#143 independently reject native word grouping literal/ordinal corruption."""
from __future__ import annotations

import unittest
from live_issue143_full_native import compare_pinned_multiword_literals


def sample(literal=b"a b"):
    return b'<multiword multiword="' + literal + b'"><norm>ab</norm></multiword>'


class RawMultiwordParityTests(unittest.TestCase):
    def test_value_must_be_source_exact_including_spaces(self):
        rec = [("demo/demo:one", sample(b"a  b"))]
        self.assertEqual(
            compare_pinned_multiword_literals(rec, {("demo/demo:one", 1): "a  b"}), 1,
        )
        with self.assertRaisesRegex(ValueError, "multiword original literal"):
            compare_pinned_multiword_literals(rec, {("demo/demo:one", 1): "a b"})

    def test_decodes_original_xml_character_entities(self):
        rec = [("demo/demo:one", sample(b"a &amp; b"))]
        self.assertEqual(
            compare_pinned_multiword_literals(rec, {("demo/demo:one", 1): "a & b"}), 1,
        )

    def test_identity_wrong_ordinal_duplicate_and_extra_nodes_fail(self):
        rec = [("demo/demo:one", sample())]
        for native in ({}, {("demo/demo:one", 2): "a b"},
                       {("demo/demo:one", 1): "a b", ("demo/demo:one", 2): "fake"}):
            with self.subTest(native=native), self.assertRaisesRegex(ValueError, "multiword"):
                compare_pinned_multiword_literals(rec, native)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compare_pinned_multiword_literals(rec + rec, {("demo/demo:one", 1): "a b"})

    def test_empty_present_lit_and_duplicate_source_attribute(self):
        self.assertEqual(
            compare_pinned_multiword_literals(
                [("demo/demo:one", sample(b""))], {("demo/demo:one", 1): ""},
            ), 1
        )
        with self.assertRaisesRegex(ValueError, "multiword missing or duplicated"):
            compare_pinned_multiword_literals(
                [("demo/demo:one", b'<multiword multiword="a" multiword="b"></multiword>')],
                {("demo/demo:one", 1): "a"},
            )


if __name__ == "__main__":
    unittest.main()
