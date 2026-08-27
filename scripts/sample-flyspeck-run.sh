#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  printf 'usage: %s <state-directory> <output.pft.bin> <supervisor-pid>\n' \
    "$0" >&2
  exit 2
fi

state_dir=$(realpath -m -- "$1")
output=$(realpath -m -- "$2")
supervisor_pid=$3
status_file="$state_dir/status.tsv"
sample_file="$state_dir/resources.tsv"
checkpoint_dir="$state_dir/checkpoints"

[[ "$supervisor_pid" =~ ^[1-9][0-9]*$ ]]
[[ -d "$state_dir" && -d "$checkpoint_dir" ]]

if [[ ! -e "$sample_file" ]]; then
  printf 'utc\tphase\tindex\tpid\trss_kib\tcpu_percent\tprocess_elapsed_s\ttrace_bytes\tcheckpoint_bytes\n' \
    >"$sample_file"
fi

while kill -0 "$supervisor_pid" 2>/dev/null; do
  utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  phase=initializing
  index=0
  if [[ -s "$status_file" ]]; then
    IFS=$'\t' read -r phase index _ <"$status_file"
  fi
  process_sample=$(
    ps -eo pid=,rss=,%cpu=,etimes=,stat=,args= |
      awk '
        /ocamlrun .*ocaml-hol|\[DMTCP:ocaml-hol\]|\[mtcp_restart\]/ {
          if ($2 > maximum) {
            maximum = $2;
            pid = $1;
            cpu = $3;
            elapsed = $4
          }
        }
        END {
          if (maximum == "") print "0 0 0.0 0";
          else print pid, maximum, cpu, elapsed
        }'
  )
  read -r process_pid rss_kib cpu_percent process_elapsed \
    <<<"$process_sample"
  trace_bytes=0
  [[ -f "$output" ]] && trace_bytes=$(stat -c '%s' "$output")
  checkpoint_bytes=$(
    find "$checkpoint_dir" -maxdepth 1 -type f \
      \( -name 'ckpt_*.dmtcp' -o -name 'ckpt_*.dmtcp.temp' \) \
      -printf '%s\n' | sort -nr | head -n 1
  )
  checkpoint_bytes=${checkpoint_bytes:-0}
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$utc" "$phase" "$index" "$process_pid" "$rss_kib" \
    "$cpu_percent" "$process_elapsed" "$trace_bytes" \
    "$checkpoint_bytes" >>"$sample_file"
  sleep 10
done
