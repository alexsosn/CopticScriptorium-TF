"""RED CI release gate: PRs modifying CoNLL-U-native graph must run full parity."""
from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/issue66-conllu.yml"


class FullCorpusWorkflowContract(unittest.TestCase):
    def test_full_parity_runs_on_relevant_pull_requests_not_one_branch_name(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("on:\n  pull_request:\n    paths:\n", text)
        for source in (
            ".github/workflows/issue66-conllu.yml",
            "copticscriptorium_tf/conllu.py",
            "copticscriptorium_tf/converter.py",
            "copticscriptorium_tf/model.py",
            "copticscriptorium_tf/_graph_core.py",
            "copticscriptorium_tf/writer.py",
            "copticscriptorium_tf/parser.py",
            "tests/test_issue66_*.py",
        ):
            self.assertIn(f"      - '{source}'", text)
        full_job = text.split("  conllu-full-corpus-parity:", 1)[1]
        header = full_job.split("    needs:", 1)[0]
        self.assertNotIn("    if:", header)
        self.assertNotIn("feat/issue66-conllu-supplement", text)
        self.assertIn("      - name: Convert, reload and independently reread CoNLL-U", full_job)
        self.assertIn("--output", full_job)


if __name__ == "__main__":
    unittest.main()
