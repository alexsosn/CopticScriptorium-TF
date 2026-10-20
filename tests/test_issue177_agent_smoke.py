"""RED-first contract for a real installed-user journey on immutable Coptic TT."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/issue177-agent-user-smoke.yml"
SCRIPT = ROOT / "tests/live_issue177_agent_user_smoke.py"
PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"


class InstalledResearcherJourneyContract(unittest.TestCase):
    def test_real_immutable_sources_and_clean_wheel_are_required(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for required in (
            "on:", "pull_request:", "actions/checkout@v4",
            "github.event.pull_request.head.sha",
            "CopticScriptorium/corpora", PIN,
            "/thomas-gospel/thomas.gospel_TT/thomas_gospel.tt",
            "/pistis-sophia/pistis.sophia_TT/pistis.sophia_book_1_part1.tt",
            "python -m build --wheel", "python -m venv",
            "dist/*.whl", "live_issue177_agent_user_smoke.py",
            "Verify exact installed-user smoke and negative path",
        ):
            with self.subTest(contract=required):
                self.assertIn(required, workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("--source /path/to", workflow)

    def test_real_browser_http_query_journey_is_exercised(self):
        script = SCRIPT.read_text(encoding="utf-8")
        # Real loopback WSGI request/response, rather than only --check.
        for fragment in (
            "from tf.browser.web import setup as setup_browser",
            "from werkzeug.serving import make_server",
            "from urllib.request import Request, urlopen",
            "from urllib.parse import urlencode",
            "127.0.0.1",
            '"/query"',
            'method="POST"',
            '"nResults"',
            '"status"',
            '"http_browser_search"',
        ):
            with self.subTest(browser_contract=fragment):
                self.assertIn(fragment, script)
        self.assertIn(\'"condenseType": "document"\', script)
        self.assertIn("server.shutdown()", script)
        self.assertIn("server.server_close()", script)
        self.assertNotIn("print(page_html)", script)
        self.assertNotIn("print(query_html)", script)

    def test_smoke_uses_public_cli_fabric_and_browser_not_converter_internals(self):
        script = SCRIPT.read_text(encoding="utf-8")
        for required in (
            "copticscriptorium-tf", "copticscriptorium-tf-web",
            "from tf.fabric import Fabric", PIN,
            "source_sha256", "trans_horner", "horner_span",
            "dependency_head", "no supported TT source records",
            "text-orig-full", "CONLLU",
        ):
            with self.subTest(contract=required):
                self.assertIn(required, script)
        self.assertNotIn("from copticscriptorium_tf.", script)
        self.assertNotIn("import copticscriptorium_tf.", script)
        self.assertNotIn("print(raw", script)
        self.assertNotIn("proc.stderr[-", script)
        self.assertNotIn('result["upstream_commit"]', script)
        self.assertIn('result["slots"]', script)
        self.assertIn("stderr_sha256", script)


if __name__ == "__main__":
    unittest.main()
