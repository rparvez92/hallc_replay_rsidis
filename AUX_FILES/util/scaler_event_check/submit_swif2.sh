#!/bin/bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "Usage: $0 <phase1|phase2> [batch-size=50] [workflow-name]" >&2
  exit 2
fi

phase=$1
batch_size=${2:-50}
workflow=${3:-scaler_event_check_${phase}}
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
run_list="$script_dir/${phase}_scaler_event_check_runlist.csv"
fragment_dir="$script_dir/results/$phase/fragments"

if [[ "$phase" != phase1 && "$phase" != phase2 ]]; then
  echo "Phase must be phase1 or phase2" >&2
  exit 2
fi
if ! [[ "$batch_size" =~ ^[1-9][0-9]*$ ]]; then
  echo "Batch size must be a positive integer" >&2
  exit 2
fi

run_count=$(( $(wc -l < "$run_list") - 1 ))
if (( run_count <= 0 )); then
  echo "Run list is empty: $run_list" >&2
  exit 1
fi

python3 "$script_dir/generate_runlists.py" "$phase" --check
mkdir -p "$fragment_dir"
if compgen -G "$fragment_dir/batch_*.csv" > /dev/null; then
  echo "Existing CSV fragments found in $fragment_dir" >&2
  echo "Move or remove them before starting a new workflow to avoid stale results." >&2
  exit 1
fi
swif2 create -workflow "$workflow"

for ((start=0; start<run_count; start+=batch_size)); do
  fragment=$(printf "%s/batch_%06d.csv" "$fragment_dir" "$start")
  job_name=$(printf "scaler_%s_%06d" "$phase" "$start")
  swif2 add-job \
    -workflow "$workflow" \
    -name "$job_name" \
    -partition production \
    -cores 1 \
    -ram 1500MB \
    -time 1h \
    -disk 1GB \
    /bin/bash "$script_dir/run_batch.sh" "$phase" "$start" "$batch_size" "$fragment"
done

swif2 run -workflow "$workflow"
echo "Submitted $run_count runs to $workflow in batches of $batch_size."
echo "Monitor with: swif2 status -workflow $workflow"
