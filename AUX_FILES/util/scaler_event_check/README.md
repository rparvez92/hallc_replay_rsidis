# Scaler event check

This study compares the terminal `evNumber` in the applicable scaler tree(s)
with the number of physics-tree entries. A run is flagged when
`abs(evNumber - T->GetEntries()) >= 10`.

The checker runs directly with ROOT on an ifarm or cdaq machine. It does not
require a batch-submission system, hcana, or the analyzer executable.

## Layout

- `bigtable/` contains normalized input run-list CSVs.
- `macros/` contains the ROOT worker macro.
- `tools/` contains the run-list generator and direct-run shell wrapper.
- `results/` contains complete and flagged-only output CSVs.

## Run-type mapping

| Run type | Replay filename | Scaler trees |
|---|---|---|
| `PI-SIDIS`, `PI+SIDIS`, `HMSHEEP`, `SHMSHEEP` | `coin_replay_production_<run>_-1.root` | TSH and TSP |
| `HMSDIS`, `HMSHEE` | `hms_coin_replay_production_<run>_-1.root` | TSH |
| `SHMSDIS`, `SHMSHEE` | `shms_coin_replay_production_<run>_-1.root` | TSP |

## Final-QA study

`bigtable/QA_scaler_event_check_runlist.csv` contains 419 normalized rows
generated from the two-column `final_qa_runlist.csv`. To regenerate or validate
it when the source list changes:

```bash
python3 AUX_FILES/util/scaler_event_check/tools/generate_runlists.py \
  qa --qa-source /path/to/final_qa_runlist.csv

python3 AUX_FILES/util/scaler_event_check/tools/generate_runlists.py \
  qa --qa-source /path/to/final_qa_runlist.csv --check
```

Run the QA check from the `hallc_replay_rsidis` repository root:

```bash
scaler_dir="$PWD/AUX_FILES/util/scaler_event_check"

"$scaler_dir/tools/run_scaler_event_check.sh" \
  QA \
  "$scaler_dir/bigtable/QA_scaler_event_check_runlist.csv" \
  /lustre24/expphy/volatile/hallc/c-rsidis/pdbforce/replay/ROOTfiles \
  "$scaler_dir/results/scaler_event_check_QA.csv" \
  "$scaler_dir/results/scaler_event_check_QA_flagged.csv"
```

The runner checks every listed run in one ROOT process, verifies the output row
count, and creates both the complete and flagged-only CSV files. Missing files
or malformed trees remain in the complete CSV with a diagnostic `status`.

## Sample pass1 QA study

```bash
scaler_dir="$PWD/AUX_FILES/util/scaler_event_check"

"$scaler_dir/tools/run_scaler_event_check.sh" \
  sample \
  "$scaler_dir/bigtable/sample_scaler_event_check_runlist.csv" \
  /lustre24/expphy/volatile/hallc/c-rsidis/pdbforce/replay/pass1_QA_scdisc \
  "$scaler_dir/results/scaler_event_check_sample.csv" \
  "$scaler_dir/results/scaler_event_check_sample_flagged.csv"
```

## Run any custom list

The run-list schema is:

```text
run,run_type,replay_mode
```

Invoke:

```text
run_scaler_event_check.sh <label> <run-list.csv> <root-directory> <output.csv> [flagged.csv] [threshold]
```

The threshold defaults to 10. The output uses a signed difference,
`final_evNumber - T->GetEntries()`, and `overall_flag` uses its absolute value.

## Original phase run lists

The Phase 1 and Phase 2 lists come from their official DAT files:

```bash
python3 AUX_FILES/util/scaler_event_check/tools/generate_runlists.py
python3 AUX_FILES/util/scaler_event_check/tools/generate_runlists.py --check
```
