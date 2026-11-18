"""#212: release RED-first real Coptic Unicode lemma query contract."""
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests/live_issue177_agent_user_smoke.py"


class UnicodeResearcherQueryTests(unittest.TestCase):
    def test_simple_original_coptic_lemma_literal_is_safe_for_tf_search(self):
        scope = runpy.run_path(str(SCRIPT))
        self.assertIn("_safe_coptic_lemma_query", scope)
        query = scope["_safe_coptic_lemma_query"]
        self.assertEqual(query("ⲉⲓⲣⲉ"), "word lemma=ⲉⲓⲣⲉ")
        self.assertEqual(query("ϣⲁⲛ"), "word lemma=ϣⲁⲛ")
        for value in ("", "V", "ⲁ ⲃ", "ⲁ=ⲃ", "ⲁ*ⲃ", "ⲁ\nword", "ⲁ1", "[ⲁ]"):
            with self.subTest(value=value):
                self.assertIsNone(query(value))

    def test_real_source_native_and_http_both_search_same_unicode_lemma(self):
        script = SCRIPT.read_text(encoding="utf-8")
        for expected in (
            'api.S.search(lemma_query',
            'api.F.lemma.s(source_lemma)',
            '"http_browser_lemma_result_count"',
            '"native_lemma_query_hits"',
            '"native_lemma_query_sha256"',
            'encoded = urlencode(',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, script)
        self.assertNotIn("print(lemma_query)", script)
        self.assertNotIn("print(source_lemma)", script)


if __name__ == "__main__":
    unittest.main()
