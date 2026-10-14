#!/usr/bin/env python3
"""Estimate RF bunch spacing from coincidence-time peak periodicity in skim files."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import numpy as np
import ROOT
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks


SENTINEL = -999.0
SIDIS_TYPES = {"PI+SIDIS", "PI-SIDIS"}
HEEP_TYPES = {"HEEP", "HMSHEEP", "SHMSHEEP"}
CACHE_COLUMNS = ["run", "RF_signal", "branch", "entries_used", "status"]


def index_skim_files(directory: Path) -> dict[int, Path]:
    files: dict[int, Path] = {}
    pattern = re.compile(r"_(\d+)_-1\.root$")
    for path in directory.glob("*.root"):
        match = pattern.search(path.name)
        if match:
            files[int(match.group(1))] = path
    return files


def estimate_spacing(path: Path, branch: str, max_events: int) -> tuple[float, int, str]:
    root_file = ROOT.TFile.Open(str(path))
    tree = root_file.Get("T") if root_file else None
    if not tree or not tree.GetBranch(branch):
        if root_file:
            root_file.Close()
        return SENTINEL, 0, "missing branch"
    entries = min(int(tree.GetEntries()), max_events)
    root_file.Close()
    if entries < 500:
        return SENTINEL, entries, "insufficient entries"

    values = ROOT.RDataFrame("T", str(path)).Range(entries).AsNumpy([branch])[branch]
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (np.abs(values) < 150.0)]
    if len(values) < 500:
        return SENTINEL, len(values), "insufficient finite entries"

    edges = np.arange(-150.0, 150.1001, 0.1)
    histogram, _ = np.histogram(values, bins=edges)
    smoothed = gaussian_filter1d(histogram.astype(float), 1.0)
    baseline = gaussian_filter1d(smoothed, 20.0)
    comb = np.clip(smoothed - baseline, 0.0, None)

    lags = np.arange(15, 46)  # Trial periods from 1.5 through 4.5 ns.
    scores = []
    for lag in lags:
        left, right = comb[:-lag], comb[lag:]
        norm = np.sqrt(np.dot(left, left) * np.dot(right, right))
        scores.append(float(np.dot(left, right) / norm) if norm else 0.0)
    scores = np.asarray(scores)
    peaks, _ = find_peaks(scores, distance=8)
    if not len(peaks) or scores[peaks].max() < 0.15:
        return SENTINEL, len(values), "no reliable periodic peak"

    maximum = scores[peaks].max()
    candidates = [peak for peak in peaks if scores[peak] >= 0.55 * maximum]
    peak = min(candidates, key=lambda candidate: lags[candidate])
    offset = 0.0
    if 0 < peak < len(scores) - 1:
        left, center, right = scores[peak - 1:peak + 2]
        denominator = left - 2.0 * center + right
        if denominator:
            offset = 0.5 * (left - right) / denominator
    spacing = 0.1 * (lags[peak] + offset)
    return round(float(spacing), 6), len(values), "measured"


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bigtable", type=Path, default=script_dir / "rp_rsidis_bigtable_pass1.csv")
    parser.add_argument(
        "--skim-root", type=Path,
        default=Path("/Volumes/T7/RSIDIS/Pass1/Data/ROOTfiles/SkimmedData"),
    )
    parser.add_argument("--output", type=Path, default=script_dir / "rf_signal_spacing.csv")
    parser.add_argument("--max-events", type=int, default=50000)
    args = parser.parse_args()

    with args.bigtable.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    skim_files = index_skim_files(args.skim_root)
    results = []
    measurable = [row for row in rows if row["run_type"] in SIDIS_TYPES | HEEP_TYPES]
    for index, row in enumerate(measurable, 1):
        run = int(row["run"])
        branch = (
            "CTime_ePiCoinTime_ROC2" if row["run_type"] in SIDIS_TYPES
            else "CTime_epCoinTime_ROC2"
        )
        path = skim_files.get(run)
        if path is None:
            spacing, entries, status = SENTINEL, 0, "missing skim file"
        else:
            spacing, entries, status = estimate_spacing(path, branch, args.max_events)
        results.append({
            "run": run, "RF_signal": spacing, "branch": branch,
            "entries_used": entries, "status": status,
        })
        if index % 100 == 0 or index == len(measurable):
            print(f"Processed {index}/{len(measurable)} coincidence runs", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CACHE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    measured = sum(row["status"] == "measured" for row in results)
    print(f"Wrote {len(results)} rows to {args.output}; measured={measured}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
