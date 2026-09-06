#!/usr/bin/env python3
"""Generate scaler-event-check run lists from the official DAT files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


RUN_TYPE_TO_MODE = {
    "PI-SIDIS": "coin",
    "PI+SIDIS": "coin",
    "HMSHEEP": "coin",
    "SHMSHEEP": "coin",
    "HMSDIS": "hms",
    "HMSHEE": "hms",
    "SHMSDIS": "shms",
    "SHMSHEE": "shms",
}

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
PHASES = {
    "phase1": (REPO_ROOT / "AUX_FILES/rsidis_runlist.dat", HERE / "phase1_scaler_event_check_runlist.csv"),
    "phase2": (REPO_ROOT / "AUX_FILES/rsidis_runlist_phaseII.dat", HERE / "phase2_scaler_event_check_runlist.csv"),
}


def parse_dat(path: Path) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    seen: set[int] = set()

    with path.open(encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            line = raw_line.strip()
            if not line or line.startswith("!"):
                continue

            fields = line.split()
            try:
                run = int(fields[0])
            except (IndexError, ValueError):
                continue

            # The DAT schema places Run_type in column 12. Do not scan the
            # free-text comment because it can repeat a run-type token.
            if len(fields) < 12 or fields[11] not in RUN_TYPE_TO_MODE:
                continue
            if run in seen:
                raise ValueError(f"{path}:{line_number}: duplicate run {run}")

            run_type = fields[11]
            seen.add(run)
            rows.append({"run": run, "run_type": run_type, "replay_mode": RUN_TYPE_TO_MODE[run_type]})

    rows.sort(key=lambda row: int(row["run"]))
    return rows


def write_csv(rows: list[dict[str, str | int]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=("run", "run_type", "replay_mode"), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("phase1", "phase2", "all"), nargs="?", default="all")
    parser.add_argument("--check", action="store_true", help="validate committed CSVs without rewriting them")
    args = parser.parse_args()

    phases = PHASES if args.phase == "all" else {args.phase: PHASES[args.phase]}
    for phase, (source, output) in phases.items():
        rows = parse_dat(source)
        if args.check:
            with output.open(newline="", encoding="utf-8") as stream:
                existing = list(csv.DictReader(stream))
            expected = [{key: str(value) for key, value in row.items()} for row in rows]
            if existing != expected:
                raise SystemExit(f"{output} is not synchronized with {source}")
            action = "validated"
        else:
            write_csv(rows, output)
            action = "wrote"
        print(f"{phase}: {action} {len(rows)} runs in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
