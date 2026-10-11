"""#109 immutable-source phase measurement acceptance, piggybacks on full native TF."""
from __future__ import annotations

import json
from pathlib import Path
import sys

PHASES = (
    "start", "parsed_and_supplemented", "graph_built",
    "models_released", "writer_complete", "reload_complete",
)


def main(report_path: Path) -> None:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["upstream_commit"] == "3ac067f1709a0012daf39ea8da2fac79980176a5"
    assert report["source_records"] == 2_628
    assert report["slots"] == 2_394_354
    snapshots = report["memory_profile"]
    assert [row["phase"] for row in snapshots] == list(PHASES)
    previous_elapsed = 0.0
    previous_high_water = 0.0
    for row in snapshots:
        elapsed = row["elapsed_seconds"]
        peak = row["peak_rss_mb"]
        current = row["current_rss_mb"]
        assert isinstance(elapsed, (int, float)) and elapsed >= previous_elapsed
        assert isinstance(peak, (int, float)) and peak >= previous_high_water
        assert current is None or (isinstance(current, (int, float)) and current >= 0)
        if current is not None:
            assert current <= peak + 5.0, (row["phase"], current, peak)
        previous_elapsed, previous_high_water = elapsed, peak
    # This precise full-source run is on Ubuntu Linux, so procfs must work.
    assert all(row["current_rss_mb"] is not None for row in snapshots)
    print(json.dumps({
        "result": "PASS full pinned source memory-phase audit",
        "word_slots": report["slots"],
        "source_records": report["source_records"],
        "profile": snapshots,
        "meaning": "VmRSS is current phase-boundary RSS; ru_maxrss is lifetime peak",
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue109_profile_gate.py JSON_REPORT")
    main(Path(sys.argv[1]))
