"""#182: one-level Text-Fabric browser compatibility without false sections.

The direct TF warp stays one physical document section level. This focuses
the browser app hook independently of the real HTTP pinned-source acceptance.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_CODE = ROOT / "app" / "app.py"


def fake_app(*, types=("document",), features=("source_record_id",),
             ancestors=(100,), label="sample/sample:record"):
    node_types = {1: "word", 2: "sentence", 3: "trans_horner", 100: "document"}
    api = SimpleNamespace(
        T=SimpleNamespace(sectionTypes=types, sectionFeats=features,
                          sectionFeatures=({100: label},),
                          sectionTuple=lambda node, **kwargs: ("unchanged_upstream",),
                          nodeFromSection=lambda section: 100),
        F=SimpleNamespace(
            otype=SimpleNamespace(v=node_types.get),
            source_record_id=SimpleNamespace(
                v=lambda n: label if n == 100 else None
            ),
        ),
        L=SimpleNamespace(
            u=lambda n, otype: tuple(ancestors) if otype == "document" else ()
        ),
    )
    return SimpleNamespace(api=api, sectionStrFromNode=lambda *a, **k: "original")


class SingleSectionBrowserLinkTests(unittest.TestCase):
    def _module(self):
        self.assertTrue(APP_CODE.is_file(), "RED: missing justified one-level app hook")
        return runpy.run_path(str(APP_CODE))

    def test_public_section_labels_remain_original_physical_ids(self):
        module = self._module()
        app = fake_app()
        module["_install_one_level_adapter"](app)
        for native_node in (1, 2, 3, 100):
            with self.subTest(native_node=native_node):
                self.assertEqual(app.api.T.sectionTuple(native_node), (100,))
                document = app.api.T.sectionTuple(native_node)[0]
                self.assertEqual(
                    app.api.F.source_record_id.v(document), "sample/sample:record"
                )
        self.assertEqual(app.api.T.sectionTuple(1, fillup=True), (100,))
        # Native section types, stored section labels and reverse IDs remain unchanged.
        self.assertEqual(app.api.T.sectionTypes, ("document",))
        self.assertEqual(app.api.T.sectionFeats, ("source_record_id",))
        self.assertEqual(app.api.T.sectionFeatures, ({100: "sample/sample:record"},))
        self.assertEqual(app.api.T.nodeFromSection(("sample/sample:record",)), 100)

    def test_other_tf_section_models_retain_upstream_link_behavior(self):
        module = self._module()
        app = fake_app(types=("document", "verse"), features=("source_record_id", "n"))
        module["_install_one_level_adapter"](app)
        self.assertEqual(app.sectionStrFromNode(1), "original")
        self.assertEqual(app.api.T.sectionTuple(1), ("unchanged_upstream",))

    def test_missing_or_multiple_parent_document_fails_without_inventing_label(self):
        module = self._module()
        for parents in ((), (100, 101)):
            with self.subTest(ancestors=parents):
                app = fake_app(ancestors=parents)
                module["_install_one_level_adapter"](app)
                with self.assertRaisesRegex(ValueError, "unique enclosing document"):
                    app.api.T.sectionTuple(1)

    def test_only_exact_document_id_based_onelevel_warp_is_supported(self):
        module = self._module()
        app = fake_app(features=("another_id",))
        with self.assertRaisesRegex(ValueError, "source_record_id"):
            module["_install_one_level_adapter"](app)
        app = fake_app(label="")
        module["_install_one_level_adapter"](app)
        with self.assertRaisesRegex(ValueError, "missing physical document label"):
            app.api.T.sectionTuple(1)


if __name__ == "__main__":
    unittest.main()
