"""#215: one-section browser passage adapter without TF warp fabrication."""
from pathlib import Path
from types import SimpleNamespace
import runpy
import unittest
from unittest.mock import patch

from tf.browser import web as browser_web

ROOT = Path(__file__).resolve().parents[1]
APP_CODE = ROOT / "app/app.py"


def fake_native_app():
    labels = {100: "source/a:doc", 101: "source/b:doc"}
    lookup = {v: k for k, v in labels.items()}
    api = SimpleNamespace(
        T=SimpleNamespace(
            sectionTypes=("document",),
            sectionFeats=("source_record_id",),
            sectionFromNode=lambda n: (labels[n],),
            nodeFromSection=lambda section: lookup.get(section[0]),
        ),
        F=SimpleNamespace(
            otype=SimpleNamespace(s=lambda otype: tuple(labels), v=lambda node: "document"),
            source_record_id=SimpleNamespace(v=labels.get),
        ),
    )
    return SimpleNamespace(api=api), labels


class OneSectionPassageAdapterTests(unittest.TestCase):
    def _module(self):
        return runpy.run_path(str(APP_CODE))

    def test_existing_physical_document_is_rendered_via_native_tf(self):
        scope = self._module()
        app, labels = fake_native_app()
        kernel = SimpleNamespace(app=app)
        calls = []

        def render(*args, **kwargs):
            calls.append((args, kwargs))
            return "<details class=\"pretty\">Original document</details>"

        handler = scope["_single_section_passage"]
        with patch.dict(handler.__globals__, {"composeP": render}):
            content, sec_type, sections, level = handler(
                kernel, "norm", "word lemma=ⲉⲓⲣⲉ", labels[100],
                opened=frozenset(), getx=None,
            )
        self.assertIn("<details", content)
        self.assertEqual((sec_type, sections, level),
                         ("document", (tuple(labels.values()), ()), 0))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][:6], (app, 0, "document", "norm", (100,), frozenset()))
        self.assertEqual(calls[0][0][6], labels[100])

    def test_unknown_and_forged_extra_levels_cannot_be_interpreted_as_document(self):
        scope = self._module()
        app, labels = fake_native_app()
        kernel = SimpleNamespace(app=app)
        fn = scope["_single_section_passage"]
        for kwargs in (
            {"sec0": "not-a-real-document"},
            {"sec0": labels[100], "sec1": "forged-chapter"},
            {"sec0": labels[100], "sec2": "forged-verse"},
            {"sec0": ""},
        ):
            with self.subTest(kwargs=kwargs):
                table, otype, passages, level = fn(
                    kernel, features="", query="", **kwargs
                )
                self.assertEqual((table, otype, level), ("", "document", 0))
                self.assertEqual(len(passages[0]), 2)

    def test_kernel_adapter_is_coptic_only_not_global_for_other_corpora(self):
        scope = self._module()
        app, _ = fake_native_app()
        coptic = object.__new__(scope["TfApp"])
        coptic.api = app.api
        external = SimpleNamespace(api=SimpleNamespace(
            T=SimpleNamespace(sectionTypes=("document",), sectionFeats=("source_record_id",))
        ))

        def upstream_factory(target, name):
            return SimpleNamespace(app=target, passage="upstream")

        with patch.object(browser_web, "makeTfKernel", upstream_factory):
            scope["_install_one_level_passage_kernel_adapter"]()
            wrapper = browser_web.makeTfKernel
            self.assertTrue(wrapper._coptic_one_level_passage)
            self.assertEqual(wrapper(external, "external").passage, "upstream")
            self.assertEqual(wrapper(coptic, "coptic").passage.__func__,
                             scope["_single_section_passage"])
            scope["_install_one_level_passage_kernel_adapter"]()
            self.assertIs(browser_web.makeTfKernel, wrapper)


if __name__ == "__main__":
    unittest.main()
