"""RED-first executable documentation contract for issue #18."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric

from copticscriptorium_tf.converter import convert_source_tree


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

PRIMARY_TT = """<meta corpus="alpha" document_cts_urn="urn:cts:copticLit:fixture.a" title="Alpha" license="CC-BY-4.0">
<norm_group norm_group="ab"><orig orig="AB"><translation translation="English A B"><arabic_translation arabic_translation="Arabic A B">
<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a<entity entity="person" head_tok="#u1" identity="Person">x</entity></norm>
<norm xml:id="u2" func="dep" head="#u1" pos="V" lemma="b" norm="b">b</norm>
</arabic_translation></translation></orig></norm_group>
"""

PARALLEL_TT = """<meta corpus="alpha" document_cts_urn="urn:cts:copticLit:fixture.a" title="Parallel" license="CC-BY-4.0">
<norm_group norm_group="c"><norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="c" norm="c">c</norm></norm_group>
"""


def _source(root: Path) -> None:
    directory = root / "alpha" / "alpha_TT"
    directory.mkdir(parents=True)
    (directory / "a.tt").write_text(PRIMARY_TT, encoding="utf-8")
    (directory / "b.tt").write_text(PARALLEL_TT, encoding="utf-8")


class ReadmeContractTests(unittest.TestCase):
    def test_readme_contains_current_short_path_features_queries_and_boundaries(self) -> None:
        text = README.read_text(encoding="utf-8")
        required = (
            "## Install and convert",
            "python -m pip install .",
            "python -m copticscriptorium_tf.converter",
            "## Load and query",
            "text-orig-full",
            "text-diplomatic-full",
            "source_record_id",
            "scholarly_id",
            "dependency_head",
            "entity_head",
            "same_scholarly",
            "documented_overlap",
            "witness",
            "arabic_translation",
            "7,157.1 MiB",
            "618,769,322 bytes",
            "## Agora integration status",
            "not yet canonically registered",
            "## Troubleshooting",
            "does not certify",
        )
        for value in required:
            with self.subTest(value=value):
                self.assertIn(value, text)


class DocumentedQueryContractTests(unittest.TestCase):
    def test_documented_native_tf_operations_execute_on_generated_fixture(self) -> None:
        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            _source(source)
            tf_dir = base / "tf"
            convert_source_tree(
                source,
                tf_dir,
                upstream_repository="fixture/repo",
                upstream_commit="a" * 40,
            )

            api = Fabric(locations=[str(tf_dir)], silent="deep").load(
                "norm lemma pos func source_record_id scholarly_id corpus dataset "
                "entity_class identity own_text dependency_head entity_head same_scholarly",
                silent="deep",
            )
            self.assertTrue(api)

            document = api.T.nodeFromSection(("alpha/alpha:a",))
            self.assertIsNotNone(document)
            self.assertEqual(api.F.source_record_id.v(document), "alpha/alpha:a")
            self.assertEqual(api.F.scholarly_id.v(document), "urn:cts:copticLit:fixture.a")
            self.assertEqual(api.F.corpus.v(document), "alpha")
            self.assertEqual(api.F.dataset.v(document), "alpha")

            normalized = api.T.text(document, fmt="text-orig-full")
            diplomatic = api.T.text(document, fmt="text-diplomatic-full")
            self.assertEqual(normalized, "a b ")
            self.assertIn("AB", diplomatic)

            self.assertEqual(api.F.lemma.v(1), "a")
            self.assertEqual(api.F.pos.v(2), "V")
            self.assertEqual(api.F.func.v(2), "dep")
            self.assertEqual(tuple(api.E.dependency_head.f(2)), (1,))

            entity = api.F.otype.s("entity")[0]
            self.assertEqual(api.F.entity_class.v(entity), "person")
            self.assertEqual(api.F.identity.v(entity), "Person")
            self.assertEqual(tuple(api.E.entity_head.f(entity)), (1,))

            translation = api.F.otype.s("translation")[0]
            arabic = api.F.otype.s("arabic_translation")[0]
            self.assertEqual(api.T.text(translation), "English A B")
            self.assertEqual(api.T.text(arabic), "Arabic A B")

            parallels = tuple(api.E.same_scholarly.f(document))
            self.assertEqual(len(parallels), 1)
            self.assertEqual(api.F.source_record_id.v(parallels[0]), "alpha/alpha:b")


if __name__ == "__main__":
    unittest.main()
