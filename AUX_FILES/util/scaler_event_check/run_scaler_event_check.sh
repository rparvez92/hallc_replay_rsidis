#!/bin/bash
set -euo pipefail

if [[ $# -lt 4 || $# -gt 6 ]]; then
  echo "Usage: $0 <label> <run-list.csv> <root-directory> <output.csv> [flagged.csv] [threshold]" >&2
  exit 2
fi

label=$1
run_list=$2
root_dir=$3
output_csv=$4
flagged_csv=${5:-}
threshold=${6:-10}
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if [[ ! -r "$run_list" ]]; then
  echo "Cannot read run list: $run_list" >&2
  exit 1
fi
if ! [[ "$threshold" =~ ^[0-9]+$ ]]; then
  echo "Threshold must be a non-negative integer" >&2
  exit 2
fi

run_count=$(( $(wc -l < "$run_list") - 1 ))
if (( run_count <= 0 )); then
  echo "Run list has no data rows: $run_list" >&2
  exit 1
fi

if ! command -v root >/dev/null 2>&1; then
  modules=/etc/profile.d/modules.sh
  if [[ $(type -t module) != function && -r "$modules" ]]; then
    source "$modules"
  fi
  module use /group/halla/modulefiles
  module load root/PRO
fi

mkdir -p "$(dirname "$output_csv")"
root -l -b -q "$script_dir/check_scaler_event_batch.C(\"$label\",\"$run_list\",\"$root_dir\",\"$output_csv\",0,$run_count,$threshold)"

actual_count=$(( $(wc -l < "$output_csv") - 1 ))
if (( actual_count != run_count )); then
  echo "Expected $run_count result rows, found $actual_count in $output_csv" >&2
  exit 1
fi

if [[ -n "$flagged_csv" ]]; then
  mkdir -p "$(dirname "$flagged_csv")"
  awk -F, 'NR == 1 || $13 == 1' "$output_csv" > "$flagged_csv"
  flagged_count=$(( $(wc -l < "$flagged_csv") - 1 ))
  echo "Wrote $flagged_count flagged rows to $flagged_csv"
fi

echo "Wrote $actual_count total rows to $output_csv"
