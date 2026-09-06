#!/bin/bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "Usage: $0 <phase1|phase2> <start-row> <batch-size> <output-csv>" >&2
  exit 2
fi

phase=$1
start_row=$2
batch_size=$3
output_csv=$4
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

case "$phase" in
  phase1)
    run_list="$script_dir/phase1_scaler_event_check_runlist.csv"
    root_dir="/cache/hallc/c-rsidis/analysis/replays/pass0p1/"
    ;;
  phase2)
    run_list="$script_dir/phase2_scaler_event_check_runlist.csv"
    root_dir="/net/cdaq/cdaql3data/cdaq/hallc-online-rsidis2025/ROOTfiles/"
    ;;
  *)
    echo "Unknown phase: $phase" >&2
    exit 2
    ;;
esac

modules=/etc/profile.d/modules.sh
if [[ $(type -t module) != function && -r "$modules" ]]; then
  source "$modules"
fi
module use /group/halla/modulefiles
module load analyzer/1.7.12

mkdir -p "$(dirname "$output_csv")"
analyzer -b -q "$script_dir/check_scaler_event_batch.C(\"$phase\",\"$run_list\",\"$root_dir\",\"$output_csv\",$start_row,$batch_size,10)"
