import csv
import os
import re

def hms_dir(run_number):
    return f"/work/hallc/c-rsidis/replay/pass1/REPORT_OUTPUT/HMS/PRODUCTION/replay_hms_coin_production_{run_number}_-1.report"

def shms_dir(run_number):
    return f"/work/hallc/c-rsidis/replay/pass1/REPORT_OUTPUT/SHMS/PRODUCTION/replay_shms_coin_production_{run_number}_-1.report"

def coin_dir(run_number):
    return f"/work/hallc/c-rsidis/replay/pass1/REPORT_OUTPUT/COIN/PRODUCTION/replay_coin_production_{run_number}_-1.report"

def find_variable(line_number, pattern):
    return line_number, pattern

# Mapping: variable -> (line_index, label text that must be on that line)
HMS_MAP = {
    "BCM1_Q": find_variable(46,"BCM1  Beam Cut Charge: "),
    "BCM1_I": find_variable(39,"BCM1 Beam Cut Current: "),
    "BCM2_Q": find_variable(47,"BCM2  Beam Cut Charge: "),
    "BCM2_I": find_variable(40,"BCM2 Beam Cut Current: "),
    "BCM4A_Q": find_variable(48,"BCM4A Beam Cut Charge: "),
    "BCM4A_I": find_variable(41,"BCM4A Beam Cut Current: "),
    "BCM4B_Q": find_variable(49,"BCM4B Beam Cut Charge: "),
    "BCM4B_I": find_variable(42,"BCM4B Beam Cut Current: "),
    "BCM4C_Q": find_variable(50,"BCM4C Beam Cut Charge: "),
    "BCM4C_I": find_variable(43,"BCM4C Beam Cut Current: "),
    "h_esing_Eff": find_variable(351,"E SING FID TRACK EFFIC         :"),
    "h_hadron_Eff": find_variable(352,"HADRON SING FID TRACK EFFIC    :"),
    "ps1" : find_variable(63,"Ps1_factor ="),
    "ps2" : find_variable(64,"Ps2_factor ="),
    "ps3" : find_variable(65,"Ps3_factor ="),
    "ps4" : find_variable(66,"Ps4_factor ="),
    "ps5" : find_variable(67,"Ps5_factor ="),
    "ps6" : find_variable(68,"Ps6_factor ="),
    "pTRIG3" : find_variable(126,"["),
    "pTRIG4" : find_variable(127,"["),
    "phys_triggers": find_variable(91,"Physics Triggers (current cut) :"),
    "hEL_REAL": find_variable(101,"hEL_REAL  :"),
    "pEL_REAL": find_variable(120, "pEL_REAL  :"),
    "electr_livetime": find_variable(175,"OG 6 GeV Electronic Live Time (100, 150) :"),
    "h_EL_CLEAN": find_variable(102,"hEL_CLEAN :"),
    "p_EL_CLEAN": find_variable(121,"pEL_CLEAN :"),
    "ps3_comp_livetime": find_variable(159, "Pre-Scaled Ps3 HMS Computer Live Time :"),
    "ps4_comp_livetime": find_variable(162, "Pre-Scaled Ps4 HMS Computer Live Time :")
}

SHMS_MAP = {
    "BCM1_Q": find_variable(46,"BCM1  Beam Cut Charge: "),
    "BCM1_I": find_variable(39,"BCM1 Beam Cut Current: "),
    "BCM2_Q": find_variable(47,"BCM2  Beam Cut Charge: "),
    "BCM2_I": find_variable(40,"BCM2 Beam Cut Current: "),
    "BCM4A_Q": find_variable(48,"BCM4A Beam Cut Charge: "),
    "BCM4A_I": find_variable(41,"BCM4A Beam Cut Current: "),
    "BCM4B_Q": find_variable(49,"BCM4B Beam Cut Charge: "),
    "BCM4B_I": find_variable(42,"BCM4B Beam Cut Current: "),
    "BCM4C_Q": find_variable(50,"BCM4C Beam Cut Charge: "),
    "BCM4C_I": find_variable(43,"BCM4C Beam Cut Current: "),
    "p_esing_Eff": find_variable(377,"E SING FID TRACK EFFIC         :"),
    "p_hadron_Eff": find_variable(378,"HADRON SING FID TRACK EFFIC    :"),
    "ps1" : find_variable(63,"Ps1_factor ="),
    "ps2" : find_variable(64,"Ps2_factor ="),
    "ps3" : find_variable(65,"Ps3_factor ="),
    "ps4" : find_variable(66,"Ps4_factor ="),
    "ps5" : find_variable(67,"Ps5_factor ="),
    "ps6" : find_variable(68,"Ps6_factor ="),
    "pTRIG1" : find_variable(124,"["),
    "pTRIG2" : find_variable(125,"["),
    "phys_triggers": find_variable(89,"Physics 3/4 Triggers (current cut):"),
    "hEL_REAL": find_variable(101,"hEL_REAL  :"),
    "pEL_REAL": find_variable(120, "pEL_REAL  :"),
    "electr_livetime": find_variable(167,"OG 6 GeV Electronic Live Time (100, 150) :"),
    "h_EL_CLEAN": find_variable(102,"hEL_CLEAN :"),
    "p_EL_CLEAN": find_variable(121,"pEL_CLEAN :"),
    "ps1_comp_livetime": find_variable(152, "Pre-Scaled Ps1 SHMS Computer Live Time :"),
    "ps2_comp_livetime": find_variable(155, "Pre-Scaled Ps2 SHMS Computer Live Time :")
}

COIN_MAP = {
    "BCM1_Q": find_variable(54,"HMS BCM1  Beam Cut Charge:"),
    "BCM1_I": find_variable(47,"HMS BCM1 Beam Cut Current:"),
    "BCM2_Q": find_variable(55,"HMS BCM2  Beam Cut Charge:"),
    "BCM2_I": find_variable(48,"HMS BCM2 Beam Cut Current:"),
    "BCM4A_Q": find_variable(56,"HMS BCM4A Beam Cut Charge:"),
    "BCM4A_I": find_variable(49,"HMS BCM4A Beam Cut Current:"),
    "BCM4B_Q": find_variable(57,"HMS BCM4B Beam Cut Charge:"),
    "BCM4B_I": find_variable(50,"HMS BCM4B Beam Cut Current:"),
    "BCM4C_Q": find_variable(58,"HMS BCM4C Beam Cut Charge:"),
    "BCM4C_I": find_variable(51,"HMS BCM4C Beam Cut Current:"),
    "h_esing_Eff": find_variable(648,"E SING FID TRACK EFFIC         :"),
    "h_hadron_Eff": find_variable(649,"HADRON SING FID TRACK EFFIC    :"),
    "p_esing_Eff": find_variable(507,"E SING FID TRACK EFFIC         :"),
    "p_hadron_Eff": find_variable(508,"HADRON SING FID TRACK EFFIC    :"),
    "ps1" : find_variable(105,"Ps1_factor ="),
    "ps2" : find_variable(106,"Ps2_factor ="),
    "ps3" : find_variable(107,"Ps3_factor ="),
    "ps4" : find_variable(108,"Ps4_factor ="),
    "ps5" : find_variable(109,"Ps5_factor ="),
    "ps6" : find_variable(110,"Ps6_factor ="),
    "phys_triggers": find_variable(146,"HMS Accepted Physics Triggers       :"),
    "hEL_REAL": find_variable(205,"HMS_hEL_REAL  :"),
    "electr_livetime": find_variable(278,"ROC2 OG 6 GeV Electronic Live Time (100, 150) (no BCM cut) :"),
    "helicity_C": find_variable(1248,"BCM2  Helicity Gated Charge:"),
    "helicity_A": find_variable(1258,"BCM2  Helicity Gated Charge Asymmetry:"),
    "h_EL_CLEAN": find_variable(206,"HMS_hEL_CLEAN :"),
    "p_EL_CLEAN": find_variable(180,"SHMS_pEL_CLEAN :"),
    "ps5_comp_livetime": find_variable(254,"ROC2 Pre-Scaled Ps5 ROC2 Computer Live Time (no BCM cut) :"),
    "ps6_comp_livetime": find_variable(257,"ROC2 Pre-Scaled Ps6 ROC2 Computer Live Time (no BCM cut) :"),
}

run_type_map = {
    "HMS": HMS_MAP,
    "SHMS": SHMS_MAP,
    "COIN": COIN_MAP,
}

# === Run-dependent line numbers ===
# Some report entries sit on a different line for part of the run range.
# Each entry: (first_run, last_run, {variable: line_number}), both ends included.
# The label text searched for stays the one defined in the map above.
#LINE_OVERRIDES = {
#    "HMS": [],
#    "SHMS": [],
#    "COIN": [
#        (23839, 24874, {"ps5_comp_livetime": 254, "ps6_comp_livetime": 257}),
#    ],
#}


#def mapping_for_run(spectrometer, run_number):
    # Returns the map to parse this run's report with: the standard map,
    # with any line numbers replaced for runs inside an override range.
#    mapping = dict(run_type_map[spectrometer])
#    try:
#        run = int(run_number)
#    except (TypeError, ValueError):
#        return mapping
#    for first_run, last_run, new_lines in LINE_OVERRIDES.get(spectrometer, []):
#        if first_run <= run <= last_run:
#            for var, line_number in new_lines.items():
#                _, pattern = mapping[var]
#                mapping[var] = find_variable(line_number, pattern)
#    return mapping

def parse_report_file(report_path, mapping):
    props = {}

    if not os.path.exists(report_path):
        return props

    with open(report_path, "r") as f:
        lines = f.readlines()

    for var, (line_number, pattern) in mapping.items():
        try:
            line = lines[line_number]

            # Make sure we're looking at the expected line
            if pattern not in line:
                raise ValueError(
                    f"Expected '{pattern}' on line {line_number}, "
                    f"but found:\n{line.strip()}"
                )

            # Everything after the identifying pattern
            value_string = line.split(pattern, 1)[1]

            # Extract the first numerical value
            match = re.search(
                r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?",
                value_string
            )

            if match:
                props[var] = float(match.group())
            else:
                raise ValueError(
                    f"No numerical value found after '{pattern}' "
                    f"on line {line_number}"
                )

        except (IndexError, ValueError):
            props[var] = None

    return props


def find_special_report_file(run_number):
    if os.path.exists(coin_dir(run_number)):
        return coin_dir(run_number), run_type_map["COIN"]
    elif os.path.exists(hms_dir(run_number)):
        return hms_dir(run_number), run_type_map["HMS"]
    else:
        return shms_dir(run_number), run_type_map["SHMS"]


def load_extra_info(run_number, run_type, issues=None):
    keep_cols = ["coin", "randoms", "ransubcoin", "ransubcoin_err", "normyield", "normyield_err", "ctmean", "ctsigma"]

    hms_run_types = ("HMSDIS", "HEE", "HMSHEE")
    shms_run_types = ("SHMSDIS", "SHMSHEE")

    if run_type in hms_run_types:
        extra_path = f"/work/hallc/c-rsidis/replay/pass1/REPORT_OUTPUT/HMS/PRODUCTION/output_get_good_dis_ev_{run_number}_-1.csv"
        issue_text = "missing get_good_dis_ev file"
    elif run_type in shms_run_types:
        extra_path = f"/work/hallc/c-rsidis/replay/pass1/REPORT_OUTPUT/SHMS/PRODUCTION/output_get_good_dis_ev_{run_number}_-1.csv"
        issue_text = "missing get_good_dis_ev file"
    else:
        extra_path = f"/work/hallc/c-rsidis/replay/pass1/REPORT_OUTPUT/COIN/PRODUCTION/output_get_good_coin_ev_{run_number}_-1.csv"
        issue_text = "missing get_good_coin_ev file"

    # Run types that are not expected to have a get_good_coin_ev file:
    # a missing file for these is not reported as an issue.
    no_extra_file_expected = ("SHMSHEEP", "OPTICS")

    if not os.path.exists(extra_path):
        if run_type in no_extra_file_expected:
            return {col: -999 for col in keep_cols}
        print(f"file not found for run {run_number} ({run_type}): {extra_path}")
        if issues is not None:
            issues.append({
                "run": run_number,
                "run_type": run_type,
                "issue": issue_text
            })
        return {col: -999 for col in keep_cols}

    with open(extra_path, newline="") as f:
        row = next(csv.DictReader(f), None)

    if row is None:
        return {col: -999 for col in keep_cols}

    # Each column is read on its own: a column that is absent or not a number
    # gives -999 for that column only, not for the whole run.
    values = {}
    for col in keep_cols:
        try:
            values[col] = float(row.get(col))
        except (TypeError, ValueError):
            values[col] = -999
    return values


def load_fan_table(fan_csv_path):
    # Reads the fan frequency file once: run -> {"fan_mean", "fan_stdev"}.
    fan_map = {}
    if not os.path.exists(fan_csv_path):
        print(f"⚠️ Fan frequency file not found: {fan_csv_path}")
        return fan_map

    with open(fan_csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run = str(row.get("run", "")).strip()
            if not run or run in fan_map:      # the first row for a run wins
                continue
            try:
                fan_map[run] = {
                    "fan_mean": float(row.get("mean", -999)),
                    "fan_stdev": float(row.get("stdev", -999))
                }
            except (TypeError, ValueError):
                fan_map[run] = {"fan_mean": -999, "fan_stdev": -999}
    return fan_map

def load_ihwp_table(ihwp_csv_path):
    ihwp_map = {}
    if not os.path.exists(ihwp_csv_path):
        print(f"⚠️ IHWP file not found: {ihwp_csv_path}")
        return ihwp_map

    with open(ihwp_csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run = str(row.get("run_number") or "").strip()
            if run:
                ihwp_map[run] = {
                    "IHWP": row.get("IHWP", ""),
                    "start_time": row.get("start_time", ""),
                    "stop_time": row.get("stop_time", "")
                }
    return ihwp_map

def load_coin_block_ratios(coin_block_ratios_csv_path):
    coin_block_ratios_map = {}
    if not os.path.exists(coin_block_ratios_csv_path):
        print(f"⚠️ Coin block ratios file not found: {coin_block_ratios_csv_path}")
        return coin_block_ratios_map

    with open(coin_block_ratios_csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run = row.get("run")
            if run:
                try:
                    ratio = round(float(row.get("ratio", "")), 6)
                except (TypeError, ValueError):
                    ratio = -999
                coin_block_ratios_map[str(run)] = {
                    "coinblock_ratio": ratio
                }
    return coin_block_ratios_map

def load_boil_corr(boil_corr_map_path):
    boil_corr_map = {}
    if not os.path.exists(boil_corr_map_path):
        print(f"⚠️ Boiling correction file not found: {boil_corr_map_path}")
        return boil_corr_map

    with open(boil_corr_map_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run = row.get("run")
            if run:
                boil_corr_map[str(run)] = {
                    "boil_corr": row.get("boiling_correction", "")
                }
    return boil_corr_map


# === Experiment periods ===
# RsidisI : boiling correction is computed from fan speed and beam current.
# RsidisII: boiling correction is read from boiling_correction_factors_pass1.csv.
RSIDIS_I_RUNS = (23834, 25603)
RSIDIS_II_RUNS = (27106, 28471)


def get_period(run_number):
    # Returns "RsidisI", "RsidisII", or None if the run is outside both ranges.
    try:
        run = int(run_number)
    except (TypeError, ValueError):
        return None
    if RSIDIS_I_RUNS[0] <= run <= RSIDIS_I_RUNS[1]:
        return "RsidisI"
    if RSIDIS_II_RUNS[0] <= run <= RSIDIS_II_RUNS[1]:
        return "RsidisII"
    return None


# === IHWP convention ===
# The run log writes the half-wave plate state as "IN"/"OUT" up to RsidisI and
# as 1/0 from run 27106 on. The bigtable always uses "IN"/"OUT".
IHWP_NUMERIC_FROM_RUN = RSIDIS_II_RUNS[0]      # 27106
IHWP_NUMERIC_TO_TEXT = {0: "OUT", 1: "IN"}


def normalize_ihwp(value, run_number):
    # Returns "IN", "OUT", or -999 when the run has no IHWP entry.
    # Any other text is passed through unchanged (upper-cased).
    text = "" if value is None else str(value).strip()
    if text == "":
        return -999

    try:
        numeric_convention = int(run_number) >= IHWP_NUMERIC_FROM_RUN
    except (TypeError, ValueError):
        numeric_convention = False

    if numeric_convention:
        try:
            number = float(text)               # accepts "0", "1", "0.0", "1.0"
        except ValueError:
            number = None
        if number in IHWP_NUMERIC_TO_TEXT:
            return IHWP_NUMERIC_TO_TEXT[number]

    return text.upper()


def get_boil_corr(run_number, target, f, I, boil_corr_map):
    # Returns (boil_corr, issue_text). issue_text is None when all went well.
    period = get_period(run_number)

    if period == "RsidisI":
        if target == "LH2":
            corr = compute_corr_coeff(f, I)
            if corr == -999:
                return -999, "RsidisI LH2: missing fan speed or BCM2 current"
            return corr, None
        elif target == "LD2":
            if I in (None, -999):
                return -999, "RsidisI LD2: missing BCM2 current"
            return round(1 + 0.03493 * (I / 100), 6), None
        else:
            return 1.0, None

    if period == "RsidisII":
        corr = boil_corr_map.get(str(run_number), {}).get("boil_corr", "")
        if corr in ("", None):
            return -999, "RsidisII: run not in boiling_correction_factors_pass1.csv"
        return corr, None

    return -999, "run outside RsidisI and RsidisII ranges"


# === New Kinematic Conversion Table ===
KINEMATIC_TABLE = [
    {"ebeam": 8.5831, "x": 0.25, "Q2": 3.3, "z": 0.9, "thpq": 2.0,   "hms_p": 1.531, "hms_th": 29.045, "shms_p": 6.538, "shms_th": 7.865},
    {"ebeam": 8.5831, "x": 0.25, "Q2": 3.3, "z": 0.67, "thpq": 2.0,   "hms_p": 1.531, "hms_th": 29.045, "shms_p": 4.868, "shms_th": 7.865},
    {"ebeam": 8.5831, "x": 0.25, "Q2": 3.3, "z": 0.67, "thpq": 5.2, "hms_p": 1.531, "hms_th": 29.045, "shms_p": 4.868, "shms_th": 11.075},
    {"ebeam": 8.5831, "x": 0.25, "Q2": 3.3, "z": 0.67, "thpq": 8.5, "hms_p": 1.531, "hms_th": 29.045, "shms_p": 4.868, "shms_th": 14.375},
    {"ebeam": 8.5831, "x": 0.25, "Q2": 3.3, "z": 0.5,  "thpq": 2.0,   "hms_p": 1.531, "hms_th": 29.045, "shms_p": 3.632, "shms_th": 7.865},
    {"ebeam": 8.5831, "x": 0.25, "Q2": 3.3, "z": 0.5,  "thpq": 5.2, "hms_p": 1.531, "hms_th": 29.045, "shms_p": 3.632, "shms_th": 11.075},
    {"ebeam": 8.5831, "x": 0.25, "Q2": 3.3, "z": 0.5,  "thpq": 8.5, "hms_p": 1.531, "hms_th": 29.045, "shms_p": 3.632, "shms_th": 14.375},
    {"ebeam": 8.5831, "x": 0.25, "Q2": 3.3, "z": 0.36, "thpq": 2.0,   "hms_p": 1.531, "hms_th": 29.045, "shms_p": 2.615, "shms_th": 7.865},
    {"ebeam": 10.6716, "x": 0.25, "Q2": 3.3, "z": 0.9,  "thpq": -0.8, "hms_p": 3.642, "hms_th": 16.75, "shms_p": 6.538, "shms_th": 7.51},
    {"ebeam": 10.6716, "x": 0.25, "Q2": 3.3, "z": 0.9,  "thpq": 2.0,    "hms_p": 3.642, "hms_th": 16.75, "shms_p": 6.538, "shms_th": 10.305},
    {"ebeam": 10.6716, "x": 0.25, "Q2": 3.3, "z": 0.67, "thpq": 2.0,    "hms_p": 3.642, "hms_th": 16.75, "shms_p": 4.868, "shms_th": 10.305},
    {"ebeam": 10.6716, "x": 0.25, "Q2": 3.3, "z": 0.67, "thpq": -0.8, "hms_p": 3.642, "hms_th": 16.75, "shms_p": 4.868, "shms_th": 7.51},
    {"ebeam": 10.6716, "x": 0.25, "Q2": 3.3, "z": 0.5,  "thpq": -0.8, "hms_p": 3.642, "hms_th": 16.75, "shms_p": 3.632, "shms_th": 7.51},
    {"ebeam": 10.6716, "x": 0.25, "Q2": 3.3, "z": 0.5,  "thpq": 2.0,    "hms_p": 3.642, "hms_th": 16.75, "shms_p": 3.632, "shms_th": 10.305},
    {"ebeam": 10.6716, "x": 0.25, "Q2": 3.3, "z": 0.5,  "thpq": 5.2,  "hms_p": 3.642, "hms_th": 16.75, "shms_p": 3.632, "shms_th": 13.505},
    {"ebeam": 10.6716, "x": 0.25, "Q2": 3.3, "z": 0.5,  "thpq": 8.5,  "hms_p": 3.642, "hms_th": 16.75, "shms_p": 3.632, "shms_th": 16.81},
    {"ebeam": 10.6716, "x": 0.25, "Q2": 3.3, "z": 0.36, "thpq": 2.0,    "hms_p": 3.642, "hms_th": 16.75, "shms_p": 2.615, "shms_th": 10.305},
    {"ebeam": 10.6716, "x": 0.25, "Q2": 3.3, "z": 0.5, "thpq": -0.2,    "hms_p": 3.642, "hms_th": 16.75, "shms_p": 3.632, "shms_th": 8.11},
    {"ebeam": 6.449, "x": 0.22, "Q2": 2.2, "z": 0.5, "thpq": 2.0,    "hms_p": 1.165, "hms_th": 31.278, "shms_p": 2.766, "shms_th": 8.275},
    {"ebeam": 6.449, "x": 0.22, "Q2": 2.2, "z": 0.9, "thpq": 2.0,    "hms_p": 1.165, "hms_th": 31.278, "shms_p": 4.978, "shms_th": 8.275},
    {"ebeam": 6.449, "x": 0.44, "Q2": 4.4, "z": 0.9, "thpq": 2.0,    "hms_p": 1.165, "hms_th": 44.830, "shms_p": 5.154, "shms_th": 10.240},
    {"ebeam": 6.449, "x": 0.44, "Q2": 4.4, "z": 0.67, "thpq": 2.0,   "hms_p": 1.165, "hms_th": 44.830, "shms_p": 3.837, "shms_th": 10.240},
    {"ebeam": 6.449, "x": 0.44, "Q2": 4.4, "z": 0.52, "thpq": 2.0,   "hms_p": 1.165, "hms_th": 44.830, "shms_p": 2.978, "shms_th": 10.240},
    {"ebeam": 10.6716, "x": 0.44, "Q2": 4.4, "z": 0.52, "thpq": -2.0,   "hms_p": 5.343, "hms_th": 15.97, "shms_p": 2.978, "shms_th": 12.87},
    {"ebeam": 10.6716, "x": 0.44, "Q2": 4.4, "z": 0.52, "thpq": 0.0,   "hms_p": 5.343, "hms_th": 15.97, "shms_p": 2.978, "shms_th": 14.87},
    {"ebeam": 10.6716, "x": 0.44, "Q2": 4.4, "z": 0.52, "thpq": 2.0,   "hms_p": 5.343, "hms_th": 15.97, "shms_p": 2.978, "shms_th": 16.87},
    # ================= RsidisII (runs 27106-28471) =================
    # Settings that repeat RsidisI ones (e.g. 6.4724 GeV at hms_th=44.83 or 31.28)
    # are matched by the RsidisI rows above thanks to the ebeam tolerance.
    # --- ebeam 6.4724 ---
    {"ebeam": 6.4724, "x": 0.16, "Q2": 1.6, "z": 0.5, "thpq": 2.0, "hms_p": 1.165, "hms_th": 26.6, "shms_p": 2.738, "shms_th": 7.5},
    {"ebeam": 6.4724, "x": 0.16, "Q2": 1.6, "z": 0.9, "thpq": 2.0, "hms_p": 1.165, "hms_th": 26.6, "shms_p": 4.929, "shms_th": 7.5},
    {"ebeam": 6.4724, "x": 0.31, "Q2": 3.1, "z": 0.5, "thpq": 2.0, "hms_p": 1.165, "hms_th": 37.33, "shms_p": 2.806, "shms_th": 9.23},
    {"ebeam": 6.4724, "x": 0.31, "Q2": 3.1, "z": 0.9, "thpq": 2.0, "hms_p": 1.165, "hms_th": 37.33, "shms_p": 5.051, "shms_th": 9.23},
    {"ebeam": 6.4724, "x": 0.31, "Q2": 3.1, "z": 0.5, "thpq": 2.2, "hms_p": 1.165, "hms_th": 37.325, "shms_p": 2.806, "shms_th": 9.43},
    # --- ebeam 8.5814 ---
    {"ebeam": 8.5814, "x": 0.16, "Q2": 1.6, "z": 0.5, "thpq": 2.0, "hms_p": 3.254, "hms_th": 13.76, "shms_p": 2.738, "shms_th": 10.125},
    {"ebeam": 8.5814, "x": 0.16, "Q2": 1.6, "z": 0.9, "thpq": 2.0, "hms_p": 3.254, "hms_th": 13.76, "shms_p": 4.929, "shms_th": 10.125},
    {"ebeam": 8.5814, "x": 0.16, "Q2": 1.6, "z": 0.5, "thpq": 2.0, "hms_p": 3.254, "hms_th": 13.76, "shms_p": 2.661, "shms_th": 10.12},
    {"ebeam": 8.5814, "x": 0.16, "Q2": 1.6, "z": 0.5, "thpq": 0.0, "hms_p": 3.254, "hms_th": 13.755, "shms_p": 2.738, "shms_th": 8.12},
    {"ebeam": 8.5814, "x": 0.16, "Q2": 1.6, "z": 0.5, "thpq": 0.1, "hms_p": 3.254, "hms_th": 13.76, "shms_p": 2.738, "shms_th": 8.26},
    {"ebeam": 8.5814, "x": 0.22, "Q2": 2.2, "z": 0.5, "thpq": 2.0, "hms_p": 3.254, "hms_th": 16.13, "shms_p": 2.766, "shms_th": 11.405},
    {"ebeam": 8.5814, "x": 0.22, "Q2": 2.2, "z": 0.9, "thpq": 2.0, "hms_p": 3.254, "hms_th": 16.13, "shms_p": 4.978, "shms_th": 11.415},
    {"ebeam": 8.5814, "x": 0.22, "Q2": 2.2, "z": 0.5, "thpq": -1.0, "hms_p": 3.254, "hms_th": 16.13, "shms_p": 2.766, "shms_th": 8.405},
    {"ebeam": 8.5814, "x": 0.31, "Q2": 3.1, "z": 0.5, "thpq": 2.0, "hms_p": 3.254, "hms_th": 19.18, "shms_p": 2.806, "shms_th": 12.985},
    {"ebeam": 8.5814, "x": 0.31, "Q2": 3.1, "z": 0.9, "thpq": 2.0, "hms_p": 3.254, "hms_th": 19.18, "shms_p": 5.051, "shms_th": 12.985},
    {"ebeam": 8.5814, "x": 0.31, "Q2": 3.1, "z": 0.52, "thpq": 3.8, "hms_p": 3.254, "hms_th": 19.185, "shms_p": 2.978, "shms_th": 14.79},
    {"ebeam": 8.5814, "x": 0.44, "Q2": 4.4, "z": 0.52, "thpq": 2.0, "hms_p": 3.254, "hms_th": 22.89, "shms_p": 2.978, "shms_th": 14.79},
    {"ebeam": 8.5814, "x": 0.44, "Q2": 4.4, "z": 0.67, "thpq": 2.0, "hms_p": 3.254, "hms_th": 22.89, "shms_p": 3.837, "shms_th": 14.79},
    {"ebeam": 8.5814, "x": 0.44, "Q2": 4.4, "z": 0.9, "thpq": 2.0, "hms_p": 3.254, "hms_th": 22.89, "shms_p": 5.154, "shms_th": 14.79},
    # --- ebeam 10.6759 ---
    {"ebeam": 10.6759, "x": 0.25, "Q2": 3.3, "z": 0.5, "thpq": 11.7, "hms_p": 3.642, "hms_th": 16.75, "shms_p": 3.632, "shms_th": 20.005},
    {"ebeam": 10.6759, "x": 0.31, "Q2": 3.1, "z": 0.5, "thpq": 2.0, "hms_p": 5.343, "hms_th": 13.5, "shms_p": 2.806, "shms_th": 14.74},
    {"ebeam": 10.6759, "x": 0.31, "Q2": 3.1, "z": 0.9, "thpq": 2.0, "hms_p": 5.343, "hms_th": 13.5, "shms_p": 5.051, "shms_th": 14.74},
    {"ebeam": 10.6759, "x": 0.31, "Q2": 3.1, "z": 0.5, "thpq": -1.0, "hms_p": 5.343, "hms_th": 13.5, "shms_p": 2.806, "shms_th": 11.745},
    {"ebeam": 10.6759, "x": 0.44, "Q2": 4.4, "z": 0.67, "thpq": -2.0, "hms_p": 5.343, "hms_th": 15.97, "shms_p": 3.837, "shms_th": 12.87},
    {"ebeam": 10.6759, "x": 0.44, "Q2": 4.4, "z": 0.67, "thpq": 0.0, "hms_p": 5.343, "hms_th": 15.97, "shms_p": 3.837, "shms_th": 14.875},
    {"ebeam": 10.6759, "x": 0.44, "Q2": 4.4, "z": 0.67, "thpq": 2.0, "hms_p": 5.343, "hms_th": 15.97, "shms_p": 3.837, "shms_th": 16.87},
    {"ebeam": 10.6759, "x": 0.44, "Q2": 4.4, "z": 0.9, "thpq": 2.0, "hms_p": 5.343, "hms_th": 15.97, "shms_p": 5.154, "shms_th": 16.87},
    # HMS singles with the SHMS parked at an elastic setting: only x and Q2 are meaningful
    {"ebeam": 10.6759, "x": 0.44, "Q2": 4.4, "z": -999, "thpq": -999, "hms_p": 5.343, "hms_th": 15.965, "shms_p": 6.163, "shms_th": 20.79}
]


def find_kinematics(ebeam, hms_p, hms_th, shms_p, shms_th,
                    tol_ebeam=0.05, tol_p=0.015, tol_th=0.02):
    
    # Returns matching (x, Q2, z, thpq) for the given kinematic settings.
    # tol_ebeam lets nominally identical beam energies match across periods
    # (6.449 vs 6.4724, 8.5831 vs 8.5814, 10.6716 vs 10.6759).
    # tol_p / tol_th absorb small set-point jitter (e.g. 9.225 vs 9.235 deg)
    # while keeping distinct settings apart (closest ones differ by >0.025).
    
    for row in KINEMATIC_TABLE:
        if (
            abs(row["ebeam"] - abs(float(ebeam))) < tol_ebeam and
            abs(row["hms_p"] - abs(float(hms_p))) < tol_p and
            abs(row["hms_th"] - abs(float(hms_th))) < tol_th and
            abs(row["shms_p"] - abs(float(shms_p))) < tol_p and
            abs(row["shms_th"] - abs(float(shms_th))) < tol_th
        ):
            return {
                "x": row["x"],
                "Q2": row["Q2"],
                "z": row["z"],
                "thpq": row["thpq"]
            }
    return {"x": -999, "Q2": -999, "z": -999, "thpq": -999}

def compute_corr_coeff(f, I):
    # Fit coefficients:
    alpha2, alpha1, alpha0 = -4.77805843e-06, 1.47503555e-04,-3.17321158e-04
    beta2, beta1, beta0 = 4.53147451e-04, -1.26593244e-02, 2.89365318e-02
    gamma2, gamma1, gamma0 = -1.05667262e-02, 2.17611407e-01, 1.41933284e+02

    if any(v in (-999, None) for v in [f, I]):
        return -999

    try:
        Y_fI = ((alpha2*I**2 + alpha1*I + alpha0)*f**2 +
                (beta2*I**2 + beta1*I + beta0)*f +
                (gamma2*I**2 + gamma1*I + gamma0))
        Y_f0 = (alpha0*f**2 + beta0*f + gamma0)
        if Y_fI == 0:
            return -999
        return round(Y_f0 / Y_fI, 6)
    except Exception:
        return -999

# Helicity based charge:

def helicity_charge_hp(C,A):
    if any(v in (-999,None) for v in [C,A]):
        return -999
    else:
        BCM2_Q_hp = (C/2)*(1+A)
    return round(BCM2_Q_hp,5)

def helicity_charge_hm(C,A):
    if any(v in (-999,None) for v in [C,A]):
        return -999
    else:
        BCM2_Q_hm = (C/2)*(1-A)
    return round(BCM2_Q_hm,5)



# Which prescale triggers each report type uses for the computer livetime,
# in order of priority (the first enabled trigger wins).
LIVETIME_TRIGGERS = {
    "HMS":  ("ps3", "ps4"),
    "SHMS": ("ps1", "ps2"),
    "COIN": ("ps5", "ps6"),
}


def select_comp_livetime(props, spectrometer):
    # Returns (comp_livetime, trigger_used).
    # A trigger is enabled when its prescale factor is > 0 (-1 means disabled).
    # The livetime is read from the matching "<psN>_comp_livetime" report entry,
    # given in %, and converted to a fraction capped at 1.
    for ps in LIVETIME_TRIGGERS[spectrometer]:
        factor = props.get(ps)
        if factor is None or factor <= 0:
            continue
        livetime = props.get(f"{ps}_comp_livetime")
        if livetime is None:
            return -999, ps          # trigger enabled but its livetime line was not found
        return min(round(livetime / 100, 5), 1.0), ps
    return -999, None                # no enabled trigger


def collect_run_info(input_csv, output_csv, run_type_map):
    keep_columns = ["run", "ebeam", "target", "hms_p", "hms_th", "shms_p", "shms_th", "run_type"] 
    results = []
    issues = []

    ihwp_map = load_ihwp_table("updated_merged_run_start_stop_log_100625.csv")
    fan_map = load_fan_table("fan_freq_pass0.csv")
    coin_block_ratios_map = load_coin_block_ratios("coin_block_ratios_pass1.csv")
    boil_corr_map = load_boil_corr("boiling_correction_factors_pass1.csv")

    with open(input_csv, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            run_number = row["run"]
            run_type = row["run_type"]

            # Figure out report path depending on run type
            if run_type in ("PI-SIDIS", "PI+SIDIS", "HEEP"):
                report_path = coin_dir(run_number)
                mapping = run_type_map["COIN"]
            elif run_type in ("HMSDIS", "HEE", "HMSHEE"):
                report_path = hms_dir(run_number)
                mapping = run_type_map["HMS"]
            elif run_type in ("SHMSDIS", "SHMSHEE"):
                report_path = shms_dir(run_number)
                mapping = run_type_map["SHMS"]
            else:
                report_path, mapping = find_special_report_file(run_number)

            # Extract variables
            props = {}
            if report_path and os.path.exists(report_path):
                spectrometer = next(k for k, v in run_type_map.items() if v is mapping)
                # To use LINE_OVERRIDES again, parse with
                # mapping_for_run(spectrometer, run_number) instead of mapping.
                props = parse_report_file(report_path, mapping)

                # Electronic livetime: reports give it in %, store it as a fraction
                if props.get("electr_livetime") is not None:
                    props["electr_livetime"] = round(props["electr_livetime"] / 100, 8)

                # Computer livetime from the trigger that is actually enabled
                props["comp_livetime"], lt_trigger = select_comp_livetime(props, spectrometer)
                if props["comp_livetime"] == -999:
                    issues.append({
                        "run": run_number,
                        "run_type": run_type,
                        "issue": (f"comp_livetime: {lt_trigger} enabled but its livetime line was not found"
                                  if lt_trigger else
                                  f"comp_livetime: no enabled trigger among {LIVETIME_TRIGGERS[spectrometer]}")
                    })

                # Helicity based charge (coincidence reports only)
                if mapping is run_type_map["COIN"]:
                    props["BCM2_Q_hp"] = helicity_charge_hp(props.get("helicity_C"), props.get("helicity_A"))
                    props["BCM2_Q_hm"] = helicity_charge_hm(props.get("helicity_C"), props.get("helicity_A"))

            else:
                if report_path:  # file path expected but missing
                    print(f"⚠️ Report file not found: {report_path}")
                    issues.append({
                        "run": run_number,
                        "run_type": run_type,
                        "issue": "missing report file"
                    })
                props = {var: -999 for var in mapping.keys()}

            # Load extra info from output_get_good_coin_ev
            extra_props = load_extra_info(run_number, run_type, issues)
            props.update(extra_props)

            # Fan speed
            props.update(fan_map.get(str(run_number).strip(), {"fan_mean": -999, "fan_stdev": -999}))

            # Merge input row with extracted props
            merged = {col: row[col] for col in keep_columns if col in row}
            merged.update(props)

            # IHWP state, always written as "IN"/"OUT" (see normalize_ihwp)
            ihwp_info = ihwp_map.get(str(run_number).strip(), {})
            merged["IHWP"] = normalize_ihwp(ihwp_info.get("IHWP"), run_number)
            # merged["start_time"] = ihwp_info.get("start_time", -999)
            # merged["stop_time"] = ihwp_info.get("stop_time", -999)

            coin_block_ratio_info = coin_block_ratios_map.get(str(run_number), {})
            merged["coinblock_ratio"] = coin_block_ratio_info.get("coinblock_ratio", -999)

            try:
                kin = find_kinematics(row["ebeam"], row["hms_p"], row["hms_th"],
                                      row["shms_p"], row["shms_th"])
            except (TypeError, ValueError):
                # blank or non-numeric setting in the run list
                kin = {"x": -999, "Q2": -999, "z": -999, "thpq": -999}
                issues.append({
                    "run": run_number,
                    "run_type": run_type,
                    "issue": "kinematics: blank or non-numeric beam/spectrometer setting in run list"
                })
            merged.update(kin)

            # Boiling correction, depending on experiment period:
            #   RsidisI  (23834-25603): computed (LH2: fan speed + current fit,
            #                           LD2: linear in current, other targets: 1.0)
            #   RsidisII (27106-28471): read from boiling_correction_factors_pass1.csv
            f = merged.get("fan_mean", -999)
            I = merged.get("BCM2_I", -999)
            target = merged.get("target", "")

            boil_corr, boil_issue = get_boil_corr(run_number, target, f, I, boil_corr_map)
            merged["boil_corr"] = boil_corr
            if boil_issue:
                issues.append({
                    "run": run_number,
                    "run_type": run_type,
                    "issue": boil_issue
                })
   
            results.append(merged)

            

    # Write results to CSV
    fieldnames = keep_columns + ["x","Q2","z","thpq","BCM1_Q","BCM1_I","BCM2_Q","BCM2_I","BCM4A_Q","BCM4A_I","BCM4B_Q","BCM4B_I","BCM4C_Q","BCM4C_I","h_esing_Eff","h_hadron_Eff","p_esing_Eff","p_hadron_Eff","ps1","ps2","ps3","ps4","ps5","ps6","comp_livetime","electr_livetime",
#get_good_coin_events variables:
"coin", "ransubcoin", "ransubcoin_err", "normyield", "normyield_err", "ctmean","ctsigma",
#fan speed variables:
# "fan_mean", "fan_stdev",
"boil_corr",
#start and stop times
#"start_time", "stop_time",
"IHWP",
#helicity based charge                                 
"BCM2_Q_hp", "BCM2_Q_hm",
#coin block ratio
"coinblock_ratio",
"h_EL_CLEAN", "p_EL_CLEAN"]

    for row in results:
        for key in fieldnames:
            if key not in row or row[key] in ("", None):
                row[key] = -999

                    
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    issue_csv = output_csv.replace(".csv", "_missing_files.csv")

    with open(issue_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["run", "run_type", "issue"])
        writer.writeheader()
        writer.writerows(issues)





# ========= MAIN =========
if __name__ == "__main__":
    collect_run_info("parsed_runlist_pass1.csv", "rsidis_bigtable_pass1.csv", run_type_map)
