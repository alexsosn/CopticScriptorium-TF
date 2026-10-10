"""RED-first: real pinned writer regression must acquire only its 3 input blobs.

This inspects the *actual* production workflow; asserting an unused helper
configuration would not protect CI from a future accidental full Git clone.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/issue15-writer.yml"
WRITER_SLICE = ROOT / "research/issue-15/writer_slice.py"
PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
FILES = (
    "sahidica.mark/sahidica.mark_TT/Mark_01.tt",
    "sahidica.mark/sahidica.mark_TT/Mark_02.tt",
    "sahidica.nt/sahidica.nt_TT.zip",
)


class PinnedRealWriterSparseAcquisitionTests(unittest.TestCase):
    def test_real_checkout_selects_exact_three_pinned_source_blobs(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("repository: CopticScriptorium/corpora", workflow)
        self.assertIn(f"ref: {PIN}", workflow)
        checkout = workflow.split(
            "      - name: Checkout pinned upstream TT regression fixture\n", 1
        )[1].split("\n      - name:", 1)[0]
        self.assertIn("filter: blob:none", checkout)
        self.assertIn("sparse-checkout-cone-mode: false", checkout)
        self.assertIn("sparse-checkout: |", checkout)
        self.assertEqual(
            [line.strip() for line in checkout.splitlines()
             if line.strip().startswith("/")],
            [f"/{name}" for name in FILES],
            "only the exact required TT and ZIP blobs may be checked out",
        )
        self.assertNotIn("/*/*_TT/**", checkout)

    def test_real_job_checks_all_three_files_and_calls_actual_writer(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('test "$(git -C upstream rev-parse HEAD)" = "' + PIN + '"', workflow)
        self.assertIn("- name: Fail closed on incomplete sparse writer fixture", workflow)
        for file in FILES:
            with self.subTest(file=file):
                self.assertIn(f"test -f upstream/{file}", workflow)
        self.assertIn(
            'python research/issue-15/writer_slice.py upstream --output',
            workflow,
        )

    def test_fixture_inputs_match_production_writer_script(self):
        source = WRITER_SLICE.read_text(encoding="utf-8")
        for value in (
            "Mark_01.tt", "Mark_02.tt", "41_Mark_01.tt",
            "sahidica.mark/sahidica.mark_TT",
            "sahidica.nt/sahidica.nt_TT.zip",
        ):
            with self.subTest(value=value):
                self.assertIn(value, source)


if __name__ == "__main__":
    unittest.main()
