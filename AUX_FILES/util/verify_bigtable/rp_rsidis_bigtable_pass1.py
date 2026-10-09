#!/usr/bin/env python3
"""Build and verify the independent R-SIDIS pass1 bigtable.

The group bigtable is used only to select/order runs and to compare results.
Values in the RP table come from the runlists, replay reports, monitoring CSVs,
or the independently extracted run-plan nominal-kinematics map.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable


SENTINEL = -999
ELECTRON_MASS_GEV = 0.00051099895
PROTON_MASS_GEV = 0.9382720813
CHARGED_PION_MASS_GEV = 0.13957039

SIDIS_TYPES = {"PI-SIDIS", "PI+SIDIS"}
HMS_ELECTRON_TYPES = {"HMSDIS", "HMSHEE"}
SHMS_ELECTRON_TYPES = {"SHMSDIS", "SHMSHEE"}
COIN_REPORT_TYPES = SIDIS_TYPES | {"HMSHEEP", "SHMSHEEP", "HEEP"}

OUTPUT_COLUMNS = [
    "run", "ebeam", "target", "hms_p", "hms_th", "shms_p", "shms_th",
    "run_type", "x", "Q2", "z", "thpq", "BCM1_Q", "BCM1_I", "BCM2_Q",
    "BCM2_I", "BCM4A_Q", "BCM4A_I", "BCM4B_Q", "BCM4B_I", "BCM4C_Q",
    "BCM4C_I", "h_esing_Eff", "h_hadron_Eff", "p_esing_Eff",
    "p_hadron_Eff", "ps1", "ps2", "ps3", "ps4", "ps5", "ps6",
    "comp_livetime", "electr_livetime", "coin", "ransubcoin",
    "ransubcoin_err", "normyield", "normyield_err", "ctmean", "ctsigma",
    "boil_corr", "IHWP", "BCM2_Q_hp", "BCM2_Q_hm", "coinblock_ratio",
    "h_EL_CLEAN", "p_EL_CLEAN",
]

VERIFIED_COLUMNS = [
    "run", "ebeam", "target", "hms_p", "hms_th", "shms_p", "shms_th",
    "run_type", "x", "Q2", "z", "thpq", "BCM1_Q", "BCM1_I", "BCM2_Q",
    "BCM2_I", "BCM4A_Q", "BCM4A_I", "BCM4B_Q", "BCM4B_I", "BCM4C_Q",
    "BCM4C_I", "h_esing_Eff", "h_hadron_Eff", "p_esing_Eff",
    "p_hadron_Eff", "ps1", "ps2", "ps3", "ps4", "ps5", "ps6", "coin",
    "ransubcoin", "ransubcoin_err", "normyield", "normyield_err", "ctmean",
    "ctsigma", "h_EL_CLEAN", "p_EL_CLEAN",
]

TEXT_COLUMNS = {"target", "run_type"}
NOMINAL_COLUMNS = ("x", "Q2", "z", "thpq")
HARDWARE_TOLERANCES = {
    "ebeam": 0.05, "hms_p": 0.015, "hms_th": 0.02,
    "shms_p": 0.015, "shms_th": 0.02,
}
COHERENCE_TOLERANCES = {"x": 0.01, "Q2": 0.1, "z": 0.08, "thpq": 0.1}
RUN_SETTING_OVERRIDES = {25465: "RP008", 25466: "RP008"}

SUMMARY_COLUMNS = [
    "severity", "run", "run_type", "column", "source_file", "issue",
    "group_value", "rp_value", "difference", "note",
]

COHERENCE_COLUMNS = [
    "run", "run_type", "match_status", "coherence_status", "setting_id", "source_pages",
    "ebeam", "hms_p", "hms_th", "shms_p", "shms_th",
    "x_nominal", "x_calculated", "x_residual",
    "Q2_nominal", "Q2_calculated", "Q2_residual",
    "z_nominal", "z_calculated", "z_residual",
    "thpq_nominal", "thpq_calculated", "thpq_residual",
]


def issue(
    issues: list[dict[str, object]],
    severity: str,
    run: object,
    run_type: str,
    column: str,
    source_file: object,
    message: str,
    group_value: object = "",
    rp_value: object = "",
    difference: object = "",
    note: str = "",
) -> None:
    issues.append({
        "severity": severity,
        "run": run,
        "run_type": run_type,
        "column": column,
        "source_file": str(source_file),
        "issue": message,
        "group_value": group_value,
        "rp_value": rp_value,
        "difference": difference,
        "note": note,
    })


def read_runlist(path: Path, issues: list[dict[str, object]]) -> dict[int, dict[str, object]]:
    rows: dict[int, dict[str, object]] = {}
    with path.open() as stream:
        for line_number, raw_line in enumerate(stream, 1):
            line = raw_line.strip()
            if not line or line.startswith(("!", "#")) or set(line) == {"*"}:
                continue
            fields = re.split(r"\s+", line, maxsplit=12)
            try:
                if len(fields) < 12:
                    raise ValueError(f"expected at least 12 fields, found {len(fields)}")
                run = int(fields[0])
                row: dict[str, object] = {
                    "run": run,
                    "ebeam": float(fields[3]),
                    "target": fields[5],
                    "hms_p": float(fields[6]),
                    "hms_th": float(fields[7]),
                    "shms_p": float(fields[8]),
                    "shms_th": float(fields[9]),
                    "run_type": fields[11],
                }
                if run in rows:
                    raise ValueError("duplicate run number")
                rows[run] = row
            except (ValueError, IndexError) as exc:
                issue(
                    issues, "error", "", "", "run", path,
                    "malformed runlist row", note=f"line {line_number}: {exc}",
                )
    return rows


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return reader.fieldnames, list(reader)


def report_paths(report_root: Path, run: int) -> dict[str, Path]:
    return {
        "COIN": report_root / "COIN" / "PRODUCTION" / f"replay_coin_production_{run}_-1.report",
        "HMS": report_root / "HMS" / "PRODUCTION" / f"replay_hms_coin_production_{run}_-1.report",
        "SHMS": report_root / "SHMS" / "PRODUCTION" / f"replay_shms_coin_production_{run}_-1.report",
    }


def choose_report(report_root: Path, run: int, run_type: str) -> tuple[str, Path]:
    paths = report_paths(report_root, run)
    if run_type in COIN_REPORT_TYPES:
        return "COIN", paths["COIN"]
    if run_type in HMS_ELECTRON_TYPES:
        return "HMS", paths["HMS"]
    if run_type in SHMS_ELECTRON_TYPES:
        return "SHMS", paths["SHMS"]
    for spectrometer in ("COIN", "HMS", "SHMS"):
        if paths[spectrometer].exists():
            return spectrometer, paths[spectrometer]
    return "SHMS", paths["SHMS"]


NUMBER_RE = re.compile(r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?")


def value_after_label(line: str, label: str) -> float:
    match = NUMBER_RE.search(line.split(label, 1)[1])
    if match is None:
        raise ValueError("no numeric value after label")
    return float(match.group())


def normalize_report_text(text: str) -> str:
    """Collapse report alignment whitespace without changing its meaning."""
    return " ".join(text.strip().split())


def unique_label_value(
    lines: Iterable[str],
    label: str,
    run: int,
    run_type: str,
    column: str,
    source: Path,
    issues: list[dict[str, object]],
) -> float:
    normalized_label = normalize_report_text(label)
    matches = [
        normalize_report_text(line)
        for line in lines
        if normalize_report_text(line).startswith(normalized_label)
    ]
    if len(matches) != 1:
        issue(
            issues, "error", run, run_type, column, source,
            "report label occurrence count is not one",
            rp_value=SENTINEL, note=f"label={label!r}; occurrences={len(matches)}",
        )
        return SENTINEL
    try:
        return value_after_label(matches[0], normalized_label)
    except ValueError as exc:
        issue(
            issues, "error", run, run_type, column, source,
            "malformed report value", rp_value=SENTINEL, note=str(exc),
        )
        return SENTINEL


def efficiency_values(
    lines: list[str],
    report_type: str,
    run: int,
    run_type: str,
    source: Path,
    issues: list[dict[str, object]],
) -> dict[str, float]:
    result = {
        "h_esing_Eff": SENTINEL,
        "h_hadron_Eff": SENTINEL,
        "p_esing_Eff": SENTINEL,
        "p_hadron_Eff": SENTINEL,
    }
    e_lines = [line for line in lines if line.lstrip().startswith("E SING FID TRACK EFFIC")]
    h_lines = [line for line in lines if line.lstrip().startswith("HADRON SING FID TRACK EFFIC")]
    expected = 2 if report_type == "COIN" else 1
    if len(e_lines) != expected or len(h_lines) != expected:
        for column in result:
            issue(
                issues, "error", run, run_type, column, source,
                "tracking-efficiency label count is unexpected", rp_value=SENTINEL,
                note=f"E occurrences={len(e_lines)}; hadron occurrences={len(h_lines)}; expected={expected}",
            )
        return result
    try:
        e_values = [value_after_label(line, "E SING FID TRACK EFFIC") for line in e_lines]
        h_values = [value_after_label(line, "HADRON SING FID TRACK EFFIC") for line in h_lines]
    except ValueError as exc:
        issue(
            issues, "error", run, run_type, "tracking_efficiencies", source,
            "malformed tracking-efficiency value", rp_value=SENTINEL, note=str(exc),
        )
        return result
    if report_type == "COIN":
        result.update({
            "p_esing_Eff": e_values[0], "p_hadron_Eff": h_values[0],
            "h_esing_Eff": e_values[1], "h_hadron_Eff": h_values[1],
        })
    elif report_type == "HMS":
        result.update({"h_esing_Eff": e_values[0], "h_hadron_Eff": h_values[0]})
    else:
        result.update({"p_esing_Eff": e_values[0], "p_hadron_Eff": h_values[0]})
    return result


def parse_report(
    path: Path,
    report_type: str,
    run: int,
    run_type: str,
    issues: list[dict[str, object]],
) -> dict[str, float]:
    derived_columns = [
        "BCM1_Q", "BCM1_I", "BCM2_Q", "BCM2_I", "BCM4A_Q", "BCM4A_I",
        "BCM4B_Q", "BCM4B_I", "BCM4C_Q", "BCM4C_I", "h_esing_Eff",
        "h_hadron_Eff", "p_esing_Eff", "p_hadron_Eff", "ps1", "ps2",
        "ps3", "ps4", "ps5", "ps6", "h_EL_CLEAN", "p_EL_CLEAN",
    ]
    if not path.exists():
        issue(issues, "error", run, run_type, "report", path, "missing report file")
        return {column: SENTINEL for column in derived_columns}

    lines = path.read_text(errors="replace").splitlines()
    prefix = "HMS " if report_type == "COIN" else ""
    result: dict[str, float] = {}
    for bcm in ("BCM1", "BCM2", "BCM4A", "BCM4B", "BCM4C"):
        result[f"{bcm}_Q"] = unique_label_value(
            lines, f"{prefix}{bcm} Beam Cut Charge:", run, run_type,
            f"{bcm}_Q", path, issues,
        )
        result[f"{bcm}_I"] = unique_label_value(
            lines, f"{prefix}{bcm} Beam Cut Current:", run, run_type,
            f"{bcm}_I", path, issues,
        )

    for number in range(1, 7):
        result[f"ps{number}"] = unique_label_value(
            lines, f"Ps{number}_factor =", run, run_type,
            f"ps{number}", path, issues,
        )

    clean_labels = (
        ("HMS_hEL_CLEAN :", "SHMS_pEL_CLEAN :")
        if report_type == "COIN"
        else ("hEL_CLEAN :", "pEL_CLEAN :")
    )
    result["h_EL_CLEAN"] = unique_label_value(
        lines, clean_labels[0], run, run_type, "h_EL_CLEAN", path, issues,
    )
    result["p_EL_CLEAN"] = unique_label_value(
        lines, clean_labels[1], run, run_type, "p_EL_CLEAN", path, issues,
    )
    for column in ("h_EL_CLEAN", "p_EL_CLEAN"):
        value = result[column]
        if value != SENTINEL and not float(value).is_integer():
            issue(
                issues, "error", run, run_type, column, path,
                "EL_CLEAN report value is not an integer", rp_value=SENTINEL,
                note=f"value={value}",
            )
            result[column] = SENTINEL
        else:
            result[column] = int(value)
    result.update(efficiency_values(lines, report_type, run, run_type, path, issues))
    return result


def monitor_csv_path(report_root: Path, report_type: str, run: int) -> Path:
    directory = report_root / report_type / "PRODUCTION"
    if report_type == "COIN":
        return directory / f"output_get_good_coin_ev_{run}_-1.csv"
    return directory / f"output_get_good_dis_ev_{run}_-1.csv"


def parse_monitor_csv(
    path: Path,
    report_type: str,
    run: int,
    run_type: str,
    issues: list[dict[str, object]],
) -> dict[str, float]:
    columns = [
        "coin", "ransubcoin", "ransubcoin_err", "normyield", "normyield_err",
        "ctmean", "ctsigma",
    ]
    result = {column: SENTINEL for column in columns}
    expected = run_type in SIDIS_TYPES | {"HMSDIS", "SHMSDIS"}
    if not path.exists():
        if expected:
            issue(issues, "error", run, run_type, "monitor_csv", path, "missing output CSV file")
        return result

    try:
        _, rows = read_csv_rows(path)
    except (OSError, ValueError, csv.Error) as exc:
        issue(
            issues, "error", run, run_type, "monitor_csv", path,
            "unreadable output CSV file", note=str(exc),
        )
        return result
    if len(rows) != 1:
        issue(
            issues, "error", run, run_type, "monitor_csv", path,
            "output CSV does not contain exactly one data row", note=f"rows={len(rows)}",
        )
        return result
    row = rows[0]
    if row.get("runnum") not in (None, "") and int(float(row["runnum"])) != run:
        issue(
            issues, "error", run, run_type, "runnum", path,
            "output CSV run number mismatch", rp_value=row.get("runnum", ""),
        )

    available = columns if report_type == "COIN" else ["normyield", "normyield_err"]
    for column in available:
        raw_value = row.get(column)
        if raw_value in (None, ""):
            issue(
                issues, "error", run, run_type, column, path,
                "missing output CSV column or value", rp_value=SENTINEL,
            )
            continue
        try:
            result[column] = float(raw_value)
        except ValueError:
            issue(
                issues, "error", run, run_type, column, path,
                "malformed output CSV value", rp_value=SENTINEL, note=f"value={raw_value!r}",
            )
    return result


def electron_kinematics(ebeam: float, momentum: float, theta_deg: float) -> tuple[float, float, float, float]:
    momentum = abs(momentum)
    theta = math.radians(abs(theta_deg))
    electron_energy = math.sqrt(momentum * momentum + ELECTRON_MASS_GEV**2)
    nu = ebeam - electron_energy
    q2 = 4.0 * ebeam * electron_energy * math.sin(theta / 2.0) ** 2
    if nu <= 0.0 or q2 <= 0.0:
        raise ValueError(f"nonphysical central setting: nu={nu}, Q2={q2}")
    x = q2 / (2.0 * PROTON_MASS_GEV * nu)
    theta_q = math.degrees(math.atan2(
        electron_energy * math.sin(theta),
        ebeam - electron_energy * math.cos(theta),
    ))
    return x, q2, nu, theta_q


def calculate_continuous_kinematics(row: dict[str, object]) -> dict[str, float]:
    result = {"x": SENTINEL, "Q2": SENTINEL, "z": SENTINEL, "thpq": SENTINEL}
    try:
        # Every accepted nominal-map entry uses the SIDIS setting convention:
        # HMS is the scattered-electron arm and SHMS is the detected-pion arm.
        # This central-geometry check is valid even when the acquired trigger
        # sample is SHMSDIS, BCM, or EDTMBCM.
        x, q2, nu, theta_q = electron_kinematics(
            float(row["ebeam"]), float(row["hms_p"]), float(row["hms_th"]),
        )
        result.update({"x": x, "Q2": q2})
        pion_momentum = abs(float(row["shms_p"]))
        pion_energy = math.sqrt(pion_momentum**2 + CHARGED_PION_MASS_GEV**2)
        result["z"] = pion_energy / nu
        result["thpq"] = abs(float(row["shms_th"])) - theta_q
    except (ValueError, ZeroDivisionError):
        pass
    return result


def lookup_nominal_kinematics(
    row: dict[str, object],
    nominal_rows: list[dict[str, str]],
    nominal_map: Path,
    issues: list[dict[str, object]],
) -> tuple[dict[str, float], str, dict[str, str] | None]:
    override_id = RUN_SETTING_OVERRIDES.get(int(row["run"]))
    if override_id:
        matches = [setting for setting in nominal_rows if setting["setting_id"] == override_id]
        if len(matches) != 1:
            raise ValueError(f"setting override {override_id} is absent or duplicated")
        issue(
            issues, "info", row["run"], str(row["run_type"]), "kinematics",
            nominal_map, "manual nominal-setting override",
            note=f"assigned={override_id}; approved pending group decision",
        )
    else:
        matches = [
            setting for setting in nominal_rows
            if all(
                abs(abs(float(row[column])) - abs(float(setting[column]))) < tolerance
                for column, tolerance in HARDWARE_TOLERANCES.items()
            )
        ]
    result = {column: SENTINEL for column in NOMINAL_COLUMNS}
    if not matches:
        def normalized_distance(setting: dict[str, str]) -> float:
            return max(
                abs(abs(float(row[column])) - abs(float(setting[column]))) / tolerance
                for column, tolerance in HARDWARE_TOLERANCES.items()
            )

        nearest = min(nominal_rows, key=normalized_distance)
        failures = []
        for column, tolerance in HARDWARE_TOLERANCES.items():
            difference = abs(float(row[column])) - abs(float(nearest[column]))
            if abs(difference) >= tolerance:
                failures.append(f"{column}={difference:+.6g} (tol={tolerance})")
        issue(
            issues, "warning", row["run"], str(row["run_type"]), "kinematics",
            nominal_map, "no nominal-setting map match",
            note=(
                f"nearest={nearest['setting_id']}; outside=" + ";".join(failures)
            ),
        )
        return result, "unmatched", None
    nominal_labels = {
        (setting["x"], setting["Q2"], setting["z"], setting["theta_pq"])
        for setting in matches
    }
    if len(nominal_labels) > 1:
        issue(
            issues, "error", row["run"], str(row["run_type"]), "kinematics",
            nominal_map, "multiple authoritative nominal-setting matches",
            note="|".join(setting["setting_id"] for setting in matches),
        )
        return result, "ambiguous", None
    setting = matches[0]
    result.update({
        "x": float(setting["x"]),
        "Q2": float(setting["Q2"]),
        "z": float(setting["z"]),
        "thpq": float(setting["theta_pq"]),
    })
    return result, "matched", setting


def numeric(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def values_equal(column: str, group_value: object, rp_value: object) -> tuple[bool, object]:
    if column in TEXT_COLUMNS:
        return str(group_value).strip() == str(rp_value).strip(), ""
    group_number = numeric(group_value)
    rp_number = numeric(rp_value)
    if group_number is None or rp_number is None:
        return str(group_value) == str(rp_value), ""
    difference = rp_number - group_number
    if group_number == SENTINEL or rp_number == SENTINEL:
        return group_number == rp_number, difference
    return math.isclose(group_number, rp_number, rel_tol=0.0, abs_tol=1e-9), difference


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def build(args: argparse.Namespace) -> int:
    if not args.report_root.is_dir():
        raise FileNotFoundError(
            f"report root is unavailable; refusing to generate degraded output: {args.report_root}"
        )
    if not args.group_csv.is_file():
        raise FileNotFoundError(f"group reference CSV is unavailable: {args.group_csv}")
    if not args.nominal_map.is_file():
        raise FileNotFoundError(f"nominal run-plan map is unavailable: {args.nominal_map}")
    for runlist in args.runlists:
        if not runlist.is_file():
            raise FileNotFoundError(f"runlist is unavailable: {runlist}")

    issues: list[dict[str, object]] = []
    _, nominal_rows = read_csv_rows(args.nominal_map)
    group_header, group_rows = read_csv_rows(args.group_csv)
    if group_header != OUTPUT_COLUMNS:
        issue(
            issues, "error", "ALL", "", "header", args.group_csv,
            "group CSV header differs from expected pass1 schema",
            group_value="|".join(group_header), rp_value="|".join(OUTPUT_COLUMNS),
        )
    group_runs = [int(row["run"]) for row in group_rows]
    duplicate_runs = sorted(run for run, count in Counter(group_runs).items() if count > 1)
    if duplicate_runs:
        issue(
            issues, "error", "ALL", "", "run", args.group_csv,
            "duplicate run numbers in group CSV", note=str(duplicate_runs),
        )

    runlist_rows: dict[int, dict[str, object]] = {}
    for runlist in args.runlists:
        for run, row in read_runlist(runlist, issues).items():
            if run in runlist_rows:
                issue(
                    issues, "error", run, str(row["run_type"]), "run", runlist,
                    "run occurs in more than one runlist",
                )
            runlist_rows[run] = row

    rp_rows: list[dict[str, object]] = []
    coherence_rows: list[dict[str, object]] = []
    group_by_run = {int(row["run"]): row for row in group_rows}
    for run in group_runs:
        group_row = group_by_run[run]
        if run not in runlist_rows:
            issue(
                issues, "error", run, group_row.get("run_type", ""), "run",
                "|".join(str(path) for path in args.runlists),
                "group run is absent from current runlists",
            )
            base = {column: SENTINEL for column in OUTPUT_COLUMNS}
            base.update({"run": run, "run_type": group_row.get("run_type", SENTINEL)})
            rp_rows.append(base)
            continue

        runlist_row = runlist_rows[run]
        run_type = str(runlist_row["run_type"])
        result: dict[str, object] = {column: SENTINEL for column in OUTPUT_COLUMNS}
        result.update({column: runlist_row[column] for column in (
            "run", "ebeam", "target", "hms_p", "hms_th", "shms_p", "shms_th", "run_type",
        )})
        nominal, match_status, setting = lookup_nominal_kinematics(
            runlist_row, nominal_rows, args.nominal_map, issues,
        )
        result.update(nominal)
        calculated = calculate_continuous_kinematics(runlist_row)
        coherence: dict[str, object] = {
            "run": run,
            "run_type": run_type,
            "match_status": match_status,
            "setting_id": setting["setting_id"] if setting else "",
            "source_pages": (
                setting.get("source_pages", setting.get("source_reference", ""))
                if setting else ""
            ),
            **{column: runlist_row[column] for column in HARDWARE_TOLERANCES},
        }
        for column in NOMINAL_COLUMNS:
            nominal_value = nominal[column]
            calculated_value = calculated[column]
            coherence[f"{column}_nominal"] = nominal_value
            coherence[f"{column}_calculated"] = (
                round(calculated_value, 6) if calculated_value != SENTINEL else SENTINEL
            )
            coherence[f"{column}_residual"] = (
                round(calculated_value - nominal_value, 6)
                if calculated_value != SENTINEL and nominal_value != SENTINEL else SENTINEL
            )
        residuals = {
            column: coherence[f"{column}_residual"] for column in NOMINAL_COLUMNS
            if coherence[f"{column}_residual"] != SENTINEL
        }
        coherence["coherence_status"] = (
            "unmatched" if match_status != "matched"
            else "setting_match_only" if not residuals
            else "outlier" if any(
                abs(float(residual)) > COHERENCE_TOLERANCES[column]
                for column, residual in residuals.items()
            )
            else "coherent"
        )
        coherence_rows.append(coherence)
        report_type, report_path = choose_report(args.report_root, run, run_type)
        report_values = parse_report(report_path, report_type, run, run_type, issues)
        result.update(report_values)

        csv_path = monitor_csv_path(args.report_root, report_type, run)
        result.update(parse_monitor_csv(csv_path, report_type, run, run_type, issues))
        rp_rows.append(result)

        for column in VERIFIED_COLUMNS:
            equal, difference = values_equal(column, group_row.get(column, ""), result[column])
            if not equal:
                severity = "warning" if column in NOMINAL_COLUMNS else "error"
                issue(
                    issues, severity, run, run_type, column,
                    args.nominal_map if column in NOMINAL_COLUMNS else (
                        report_path if column not in {
                            "run", "ebeam", "target", "hms_p", "hms_th", "shms_p", "shms_th", "run_type",
                            "coin", "ransubcoin", "ransubcoin_err", "normyield", "normyield_err", "ctmean", "ctsigma",
                        } else csv_path if column in {
                            "coin", "ransubcoin", "ransubcoin_err", "normyield", "normyield_err", "ctmean", "ctsigma",
                        } else "runlist"
                    ),
                    "RP value differs from group pass1 value",
                    group_value=group_row.get(column, ""), rp_value=result[column], difference=difference,
                    note="nominal labels compared numerically and exactly" if column in NOMINAL_COLUMNS else "",
                )

    issue(
        issues, "info", "ALL", "", "BCM1_Q..BCM4C_Q", "report files",
        "charge units intentionally depend on report type",
        note="COIN values are mC; HMS/SHMS single-arm values are uC",
    )
    issue(
        issues, "info", "ALL", "", "unsupported_columns", "project scope",
        "columns outside the first verification stage use -999",
        note="comp_livetime,electr_livetime,boil_corr,IHWP,BCM2_Q_hp,BCM2_Q_hm,coinblock_ratio",
    )
    issue(
        issues, "info", "ALL", "", "run_selection", args.group_csv,
        "run membership and ordering follow the clean group reference",
        note=f"rows={len(group_runs)}",
    )
    issue(
        issues, "info", "ALL", "", "kinematic_coherence", args.kinematics_csv,
        "continuous calculations are diagnostic and do not define nominal labels",
        note="tolerances=" + ",".join(
            f"{column}:{tolerance}" for column, tolerance in COHERENCE_TOLERANCES.items()
        ),
    )

    write_csv(args.output_csv, OUTPUT_COLUMNS, rp_rows)
    write_csv(args.summary_csv, SUMMARY_COLUMNS, issues)
    write_csv(args.kinematics_csv, COHERENCE_COLUMNS, coherence_rows)
    print(f"Wrote {len(rp_rows)} rows to {args.output_csv}")
    print(f"Wrote {len(issues)} verification records to {args.summary_csv}")
    print(f"Wrote {len(coherence_rows)} kinematic records to {args.kinematics_csv}")
    print("Summary severities:", dict(Counter(str(row["severity"]) for row in issues)))
    return 1 if any(row["severity"] == "error" and row["run"] == "ALL" for row in issues) else 0


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runlists", type=Path, nargs="+",
        default=[repo_root / "AUX_FILES/rsidis_runlist.dat", repo_root / "AUX_FILES/rsidis_runlist_phaseII.dat"],
    )
    parser.add_argument(
        "--report-root", type=Path,
        default=Path("/Volumes/T7/RSIDIS/Pass1/REPORT_OUTPUT"),
    )
    parser.add_argument(
        "--group-csv", type=Path,
        default=repo_root / "AUX_FILES/rsidis_bigtable_pass1.csv",
    )
    parser.add_argument(
        "--nominal-map", type=Path,
        default=script_dir / "nominal_kinematics_map.csv",
    )
    parser.add_argument(
        "--output-csv", type=Path,
        default=script_dir / "rp_rsidis_bigtable_pass1.csv",
    )
    parser.add_argument(
        "--summary-csv", type=Path,
        default=script_dir / "varify_bigtable_summary.csv",
    )
    parser.add_argument(
        "--kinematics-csv", type=Path,
        default=script_dir / "kinematic_coherence.csv",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(build(parse_args()))
