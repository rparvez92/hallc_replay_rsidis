#!/usr/bin/env python3
"""Validate and merge SWIF2 CSV fragments for one phase."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXPECTED_FIELDS = [
    "phase", "run", "run_type", "replay_mode", "root_file", "t_entries",
    "tsh_last_evnumber", "tsh_difference", "tsh_flag",
    "tsp_last_evnumber", "tsp_difference", "tsp_flag", "overall_flag", "status",
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("phase1", "phase2"))
    parser.add_argument("--run-list", type=Path, help="override the dedicated phase run list")
    parser.add_argument("--fragment-dir", type=Path, help="override the SWIF2 fragment directory")
    parser.add_argument("--output", type=Path, help="override the consolidated output CSV")
    args = parser.parse_args()

    run_list = args.run_list or HERE / f"{args.phase}_scaler_event_check_runlist.csv"
    fragment_dir = args.fragment_dir or HERE / "results" / args.phase / "fragments"
    output = args.output or HERE / "results" / f"scaler_event_check_{args.phase}.csv"

    _, expected_rows = read_csv(run_list)
    expected = {row["run"]: row for row in expected_rows}
    fragments = sorted(fragment_dir.glob("batch_*.csv"))
    if not fragments:
        raise SystemExit(f"No fragments found in {fragment_dir}")

    merged: dict[str, dict[str, str]] = {}
    for fragment in fragments:
        fields, rows = read_csv(fragment)
        if fields != EXPECTED_FIELDS:
            raise SystemExit(f"Unexpected header in {fragment}: {fields}")
        for row in rows:
            run = row["run"]
            if run in merged:
                raise SystemExit(f"Duplicate result for run {run} (found in {fragment})")
            if run not in expected:
                raise SystemExit(f"Unexpected run {run} in {fragment}")
            reference = expected[run]
            if row["run_type"] != reference["run_type"] or row["replay_mode"] != reference["replay_mode"]:
                raise SystemExit(f"Run-list metadata mismatch for run {run}")
            if row["phase"] != args.phase:
                raise SystemExit(f"Phase mismatch for run {run}: {row['phase']}")
            merged[run] = row

    missing = sorted(set(expected) - set(merged), key=int)
    if missing:
        preview = ", ".join(missing[:20])
        raise SystemExit(f"Missing {len(missing)} expected runs: {preview}")

    ordered = [merged[run] for run in sorted(merged, key=int)]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=EXPECTED_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)

    statuses = Counter(row["status"] for row in ordered)
    flagged = sum(row["overall_flag"] == "1" for row in ordered)
    errors = sum(row["status"] not in {"OK", "DISCREPANCY"} for row in ordered)
    print(f"Wrote {len(ordered)} rows to {output}")
    print(f"OK={statuses['OK']} discrepancy={flagged} invalid_or_missing={errors}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
