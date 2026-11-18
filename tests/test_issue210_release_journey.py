"""Release #210: real researcher query and documentation parity (RED-first).

The full source/live browser checks execute in issue177-agent-installed-user-real-source-smoke;
these cheap checks ensure the key user path is not silently omitted from that job.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "tests/live_issue177_agent_user_smoke.py"
GUIDE = ROOT / "docs/researcher-guide.md"
WEB_GUIDE = ROOT / "docs/web-app.md"
QUICKSTART = ROOT / "docs/researcher-quickstart.md"
README = ROOT / "README.md"


class ResearcherReleaseJourneyContract(unittest.TestCase):
    def test_installed_source_smoke_searches_actual_pos_through_native_and_http(self):
        script = SMOKE.read_text(encoding="utf-8")
        # A generic 'word' count is not a realistic researcher search.
        for required in (
            "api.S.search(",
            "api.F.pos.s(",
            "word pos=",
            "http_browser_filtered_result_count",
            "http_browser_filtered_query",
        ):
            with self.subTest(required=required):
                self.assertIn(required, script)
        # Never assert a guessed normalized Coptic form from a different edition.
        self.assertIn("api.F.pos.v(w)", script)
        self.assertIn("nResults", script)
        self.assertNotIn("print(payload", script)
        self.assertNotIn("print(page", script)

    def test_researcher_guide_reports_verified_agora_full_acquisition(self):
        guide = GUIDE.read_text(encoding="utf-8")
        self.assertIn("Agora PR #215", guide)
        self.assertIn("automatic", guide.lower())
        self.assertIn("Context-Fabric", guide)
        self.assertNotIn("Bulk automatic Git acquisition remains an open", guide)
        self.assertNotIn("do not treat its manifest declaration as a successful full", guide)

    def test_browser_guide_distinguishes_registered_agora_from_auto_import(self):
        web = WEB_GUIDE.read_text(encoding="utf-8")
        self.assertIn("registered", web)
        self.assertIn("separate", web)
        self.assertIn("Context-Fabric", web)
        self.assertNotIn(
            "Agora\nregistration and automatic Context-Fabric/cfabric-mcp artifact discovery remain",
            web,
        )

    def test_first_researcher_journey_is_copyable_and_honest(self):
        self.assertTrue(QUICKSTART.is_file())
        quickstart = QUICKSTART.read_text(encoding="utf-8")
        for required in (
            "Python 3.12",
            "python -m pip install .",
            "copticscriptorium-tf \\",
            "--upstream-repository CopticScriptorium/corpora",
            "--upstream-commit",
            "copticscriptorium-tf-web /path/to/output-tf",
            "word lemma=",
            "Fabric",
            "api.S.search(",
            "agora_materialize_registered.py",
            "Context-Fabric",
            "2,628",
            "memory",
            "reference candidates",
        ):
            with self.subTest(required=required):
                self.assertIn(required, quickstart)
        self.assertNotIn("pip install copticscriptorium-tf", quickstart)
        readme = README.read_text(encoding="utf-8")
        self.assertIn("docs/researcher-quickstart.md", readme)


if __name__ == "__main__":
    unittest.main()
