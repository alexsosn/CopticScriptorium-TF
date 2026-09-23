"""RED-first regression contract for measured CI contention in issue #10."""
from __future__ import annotations

from pathlib import Path
import unittest

import yaml


WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _workflow(name: str) -> dict:
    # BaseLoader preserves the YAML `on` mapping key (PyYAML SafeLoader treats it
    # as a YAML 1.1 boolean) and is sufficient for static workflow contracts.
    return yaml.load((WORKFLOWS / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


class HistoricalCensusGatingTests(unittest.TestCase):
    def test_historical_audits_are_manual_without_dropping_focused_pr_checks(self) -> None:
        cases = (
            ("issue3-research.yml", "graph-shape-unit", "graph-shape-census", "Run focused issue 3 tests", "Build corpus-wide graph-shape census"),
            ("issue13-parser.yml", "parser-unit", "parser-census", "Run focused issue 13 unit tests", "Parse full pinned TT corpus and validate reviewed counts"),
            ("issue14-graph.yml", "graph-unit", "graph-census", "Run focused issue 14 tests", "Build and validate full graph twice"),
        )
        for file_name, unit_job, census_job, unit_step, census_step in cases:
            with self.subTest(workflow=file_name):
                config = _workflow(file_name)
                self.assertEqual(set(config["on"]), {"pull_request", "push", "workflow_dispatch"})
                self.assertIn(unit_job, config["jobs"])
                self.assertIn(census_job, config["jobs"])
                unit = config["jobs"][unit_job]
                census = config["jobs"][census_job]
                self.assertNotIn("if", unit, "ordinary implementation PR must run focused checks")
                self.assertEqual(census["if"], "github.event_name == 'workflow_dispatch'")
                self.assertEqual(census["needs"], unit_job)
                unit_steps = {step.get("name") for step in unit["steps"]}
                census_steps = {step.get("name") for step in census["steps"]}
                self.assertIn("Verify exact tested head", unit_steps)
                self.assertIn(unit_step, unit_steps)
                self.assertNotIn("Check out pinned TT source", unit_steps)
                self.assertNotIn("Check out pinned TT sources", unit_steps)
                self.assertNotIn("Check out pinned TT and CoNLL-U sources", unit_steps)
                self.assertIn("Verify exact tested head", census_steps)
                self.assertIn("Verify pinned upstream source", census_steps)
                self.assertIn(census_step, census_steps)
                self.assertIn("UPSTREAM_COMMIT", config["env"])
                self.assertEqual(len(config["env"]["UPSTREAM_COMMIT"]), 40)

    def test_full_converter_product_gate_is_not_replaced_by_historical_censuses(self) -> None:
        config = _workflow("issue16-full-converter.yml")
        self.assertIn("workflow_dispatch", config["on"])
        product = config["jobs"]["full-source-convert-reload"]
        self.assertIn("workflow_dispatch", product["if"])
        steps = {step.get("name") for step in product["steps"]}
        self.assertIn("Verify pinned source revision", steps)
        self.assertIn("Convert complete source and reload native TF", steps)


if __name__ == "__main__":
    unittest.main()
