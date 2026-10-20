"""#118: current code-level route audit for every original pinned TT tag.

The historical upstream census is immutable. A current native route is not
source-value/attribute/character-offset parity or scholarly alignment evidence.
"""
from __future__ import annotations

import csv
from pathlib import Path
import unittest

from copticscriptorium_tf import model
from copticscriptorium_tf import parser
from copticscriptorium_tf import writer

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "research/issue-118/tag_matrix.csv"
CURRENT = ROOT / "research/issue-118/current_native_type_routes.csv"

FAMILIES = (
    "TOKEN_WRAPPER_TYPES", "EDITION_WRAPPER_TYPES",
    "MULTIWORD_WRAPPER_TYPES", "REFERENCE_WRAPPER_TYPES",
    "EDITORIAL_WRAPPER_TYPES", "INTERVENTION_WRAPPER_TYPES",
    "ENTITY_SOURCE_WRAPPER_TYPES", "DOCUMENT_SOURCE_WRAPPER_TYPES",
    "ALTERNATE_REFERENCE_WRAPPER_TYPES", "RESIDUAL_SOURCE_WRAPPER_TYPES",
    "HORNER_TRANSLATION_WRAPPER_TYPES",
)
CORE = {
    "arabic": "node:arabic_translation",
    "arabic_translation": "node:arabic_translation",
    "cb_n": "node:column",
    "entity": "node:entity",
    "lang": "node:lang",
    "lb_n": "node:line",
    "meta": "node:document|feature:meta_*",
    "norm": "slot:word",
    "norm_group": "node:norm_group",
    "orig": "node:orig",
    "orig_group": "node:orig_group",
    "pb_xml_id": "node:page",
    "sbl_apparatus": "node:sbl_apparatus",
    "sbl_greek": "node:sbl_greek",
    "translation": "node:translation",
    "verse_n": "feature:verse_n|node:verse_n_marker",
    "verse_vid": "feature:verse_vid|node:verse_vid_marker",
    "vid_n": "feature:vid_n|node:vid_n_marker",
}


def rows(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class CurrentNativeTypeRoutes(unittest.TestCase):
    def test_all_101_original_tags_have_exactly_one_code_level_route(self):
        baseline = rows(BASELINE)
        current = rows(CURRENT)
        baseline_map = {row["tag"]: row for row in baseline}
        current_map = {row["tag"]: row for row in current}
        self.assertEqual(len(baseline), len(current), 101)
        self.assertEqual(len(baseline_map), len(current_map), 101)
        self.assertEqual(set(baseline_map), set(current_map))
        self.assertEqual(sum(int(v["source_occurrences"]) for v in current), 6_621_410)

        groups = {}
        for family in FAMILIES:
            for tag in getattr(model, family):
                self.assertNotIn(tag, groups, f"two native routes for {tag}")
                groups[tag] = family
        self.assertEqual(len(groups), 83)
        self.assertEqual(len(CORE), 18)
        self.assertFalse(set(groups).intersection(CORE))
        self.assertEqual(set(baseline_map), set(groups) | set(CORE))
        for tag, row in current_map.items():
            with self.subTest(tag=tag):
                old = baseline_map[tag]
                self.assertEqual(row["source_occurrences"], old["source_occurrences"])
                self.assertEqual(row["observed_attribute_keys"], old["attribute_keys"])
                self.assertEqual(row["historical_baseline_status"], old["baseline_status"])
                if tag in groups:
                    self.assertEqual(row["current_route"], "native_source_annotation")
                    self.assertEqual(row["family"], groups[tag])
                    self.assertEqual(row["native_representation"], f"node:{tag}")
                else:
                    self.assertEqual(row["current_route"], "native_core_representation")
                    self.assertEqual(row["family"], "core")
                    self.assertEqual(row["native_representation"], CORE[tag])
                self.assertEqual(row["evidence_level"], "code_dispatch_not_complete_parity")

    def test_core_layout_and_word_routes_are_not_fabricated(self):
        self.assertEqual(
            parser.LAYOUT_TAGS,
            {"pb_xml_id": ("page", "pb_xml_id"),
             "cb_n": ("column", "cb_n"),
             "lb_n": ("line", "lb_n")},
        )
        scalar = {name for name, *_ in writer._SCALAR_FEATURES}
        for field in ("verse_n", "vid_n", "verse_vid",
                      "norm", "lemma", "pos", "source_id"):
            self.assertIn(field, scalar)

    def test_audit_does_not_silently_certify_extra_source_attributes(self):
        data = {row["tag"]: row for row in rows(CURRENT)}
        self.assertEqual(data["morph"]["attribute_review"], "secondary_attribute_requires_source_parity")
        for tag in ("norm", "entity", "verse_n", "norm_group", "meta"):
            self.assertEqual(data[tag]["attribute_review"], "core_attributes_require_semantic_audit", tag)
        for tag in ("gap", "supplied", "abbr"):
            self.assertEqual(data[tag]["attribute_review"], "source_attr_features_declared", tag)
            expected = set(model.INTERVENTION_WRAPPER_KEYS[tag])
            emitted = {key for _, otype, key in writer._SOURCE_ATTR_FEATURES if otype == tag}
            self.assertEqual(emitted, expected)
        for row in data.values():
            self.assertIn(row["attribute_review"], {
                "single_attribute_route_declared",
                "source_attr_features_declared",
                "secondary_attribute_requires_source_parity",
                "core_attributes_require_semantic_audit",
            })
        self.assertNotIn("lossless", CURRENT.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
