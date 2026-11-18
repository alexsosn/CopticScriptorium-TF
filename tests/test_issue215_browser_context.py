"""#215 RED: browser search-result context link opens a real source passage.

The upstream Text-Fabric 13.1.0 result <a href="#"> is a JavaScript action.
Literal href presence alone does not demonstrate document navigation.
"""
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests/live_issue177_agent_user_smoke.py"
THOMAS = "thomas-gospel/thomas.gospel:thomas_gospel"
PISTIS = "pistis-sophia/pistis.sophia:pistis.sophia_book_1_part1"


class ResearcherContextNavigationContract(unittest.TestCase):
    def test_context_section_from_real_browser_style_link(self):
        scope = runpy.run_path(str(SCRIPT))
        extract = scope["_first_context_section"]
        html = '<div><a href="#" class="sq" tup="1">1</a>' + (
            f'<a href="#" class="pq fa fa-solar-panel" sec0="{THOMAS}" '
            'sec1="" sec2="" title="show in context"></a></div>'
        )
        self.assertEqual(extract(html, {THOMAS, PISTIS}), THOMAS)
        combined = (
            f'<a href="#" class="pq" sec0="{PISTIS}"></a>'
            f'<a href="#" class="pq" sec0="{THOMAS}"></a>'
        )
        self.assertEqual(extract(combined, {THOMAS, PISTIS}), PISTIS)

    def test_does_not_treat_unrelated_href_as_passage_context(self):
        scope = runpy.run_path(str(SCRIPT))
        extract = scope["_first_context_section"]
        invalid = (
            '<a href="#" class="sq" tup="1">1</a>',
            '<a href="/irrelevant" class="pq" sec0="sample"></a>',
            '<a href="#" class="pq"></a>',
            '<a href="#" class="pq" sec0="unknown:document"></a>',
            '<a href="#" class="pq" sec0=""></a>',
        )
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ValueError):
                extract(item, {THOMAS, PISTIS})

    def test_html_entity_in_source_id_is_decoded_once(self):
        scope = runpy.run_path(str(SCRIPT))
        extract = scope["_first_context_section"]
        self.assertEqual(
            extract('<a href="#" class="pq" sec0="a&amp;b"></a>', {"a&b"}),
            "a&b",
        )

    def test_real_http_installed_user_smoke_exercises_actual_passage_handler(self):
        script = SCRIPT.read_text(encoding="utf-8")
        for must_include in (
            '_first_context_section(',
            'address + "/passage"',
            '"http_browser_passage"',
            '"http_browser_passage_section_sha256"',
            'expected_documents=set(by_id)',
            'lemma_query=lemma_query',
        ):
            with self.subTest(fragment=must_include):
                self.assertIn(must_include, script)
        self.assertNotIn("print(passage_html)", script)
        self.assertNotIn("print(passage_payload)", script)


if __name__ == "__main__":
    unittest.main()
