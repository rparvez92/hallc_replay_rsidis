# Scaler event check

This study compares the terminal `evNumber` in the applicable scaler tree(s)
with the number of physics-tree entries. A run is flagged when
`abs(evNumber - T->GetEntries()) >= 10`.

The dedicated CSV run lists are generated from the official Phase I and Phase
II DAT files. The supported mappings are:

| Run type | Replay mode | Scaler trees |
|---|---|---|
| `PI-SIDIS`, `PI+SIDIS`, `HMSHEEP`, `SHMSHEEP` | coin | TSH and TSP |
| `HMSDIS`, `HMSHEE` | hms | TSH |
| `SHMSDIS`, `SHMSHEE` | shms | TSP |

## Generate and validate run lists

From the repository root:

```bash
python3 AUX_FILES/util/scaler_event_check/generate_runlists.py
python3 AUX_FILES/util/scaler_event_check/generate_runlists.py --check
```

## Foreground test

The arguments after the phase are the zero-based starting row, number of runs,
and output fragment. Choose ranges that cover the desired replay modes. The
worker loads `root/PRO`; no analyzer or hcana module is required.

```bash
AUX_FILES/util/scaler_event_check/run_batch.sh phase1 0 3 /tmp/phase1_scaler_test.csv
```

## Submit SWIF2 workflows

Each job processes 50 runs by default:

```bash
AUX_FILES/util/scaler_event_check/submit_swif2.sh phase1
AUX_FILES/util/scaler_event_check/submit_swif2.sh phase2
swif2 status -workflow scaler_event_check_phase1
swif2 status -workflow scaler_event_check_phase2
```

After every job completes successfully, merge and validate the fragments:

```bash
python3 AUX_FILES/util/scaler_event_check/merge_results.py phase1
python3 AUX_FILES/util/scaler_event_check/merge_results.py phase2
```

Final CSVs are written under `AUX_FILES/util/scaler_event_check/results/`.
Missing files and malformed trees remain represented as rows with diagnostic
status values.
