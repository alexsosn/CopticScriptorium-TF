"""#178 researcher-facing README contract tied to actual native source types."""
from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "copticscriptorium_tf" / "model.py"
README = ROOT / "README.md"
FAMILIES = {
    "TOKEN_WRAPPER_TYPES",
    "EDITION_WRAPPER_TYPES",
    "MULTIWORD_WRAPPER_TYPES",
    "REFERENCE_WRAPPER_TYPES",
    "EDITORIAL_WRAPPER_TYPES",
    "ENTITY_SOURCE_WRAPPER_TYPES",
    "DOCUMENT_SOURCE_WRAPPER_TYPES",
    "ALTERNATE_REFERENCE_WRAPPER_TYPES",
    "RESIDUAL_SOURCE_WRAPPER_TYPES",
    "HORNER_TRANSLATION_WRAPPER_TYPES",
}
CORE_NON_SLOT = (
    "document", "sentence", "orig_group", "norm_group", "orig",
    "page", "column", "line", "entity", "translation", "arabic_translation",
    "verse_n_marker", "vid_n_marker", "verse_vid_marker",
    "lang", "sbl_greek", "sbl_apparatus",
)


def declared_source_types() -> set[str]:
    """Derive the source kind contract independently of README content."""
    tree = ast.parse(MODEL.read_text(encoding="utf-8"))
    types: list[str] = []
    seen_families = set()
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        names = [target.id for target in statement.targets
                 if isinstance(target, ast.Name)]
        for name in names:
            if name in FAMILIES:
                seen_families.add(name)
                types.extend(ast.literal_eval(statement.value))
            if name == "INTERVENTION_WRAPPER_KEYS":
                seen_families.add(name)
                self_dict = statement.value
                if not isinstance(self_dict, ast.Dict):
                    raise AssertionError("native interventions must use explicit keys")
                types.extend(ast.literal_eval(k) for k in self_dict.keys)
    assert seen_families == FAMILIES | {"INTERVENTION_WRAPPER_KEYS"}, (
        "Native family declaration changed; update docs contract explicitly",
        seen_families,
    )
    assert len(types) == len(set(types)) == 83, "83 pinned source kind names must be distinct"
    return set(types)


class ResearcherReadmeNativeSchemaTests(unittest.TestCase):
    def test_all_native_annotation_otypes_are_discoverable(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("### Original-source annotation node families", text)
        source_section = text.split("### Original-source annotation node families", 1)[1].split(
            "## Measured full-corpus footprint", 1
        )[0]
        labeled = set(re.findall(r"`([A-Za-z][A-Za-z0-9_:.-]*)`", source_section))
        missing = declared_source_types() - labeled
        self.assertFalse(missing, f"README silently omits native source otypes: {sorted(missing)}")
        native_section = text.split("## Native TF model", 1)[1].split(
            "## Measured full-corpus footprint", 1
        )[0]
        for kind in CORE_NON_SLOT:
            with self.subTest(core_otype=kind):
                self.assertIn(f"`{kind}`", native_section)
        self.assertIn("The sole slot type is `word`", native_section)
        self.assertIn("not a Greek/Coptic word alignment", native_section)

    def test_footprints_are_labeled_by_measured_workload_not_stale_release_claim(self):
        text = README.read_text(encoding="utf-8")
        section = text.split("## Measured full-corpus footprint", 1)[1].split(
            "## Agora integration status", 1
        )[0]
        self.assertIn("38258054937", section)
        self.assertIn("143 TF files", section)
        self.assertIn("669,347,470 bytes", section)
        self.assertIn("7,847.0 MiB", section)
        self.assertIn("38258055163", section)
        self.assertIn("174 TF files", section)
        self.assertIn("794,868,039 bytes", section)
        self.assertIn("8,758.7 MiB", section)
        for stale in ("7,157.1 MiB", "618,769,322 bytes", "130 TF files", "about 7m47s"):
            self.assertNotIn(stale, section)
        self.assertNotIn("roughly 7.0 GiB", text)
        self.assertNotIn("- #66 — add validated CoNLL-U supplementation", text)


if __name__ == "__main__":
    unittest.main()
