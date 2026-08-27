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
sample_interval=${CANDLE_RESOURCE_SAMPLE_INTERVAL:-10}
sample_once=${CANDLE_RESOURCE_SAMPLE_ONCE:-0}

[[ "$supervisor_pid" =~ ^[1-9][0-9]*$ ]]
[[ "$sample_interval" =~ ^[1-9][0-9]*$ ]]
[[ "$sample_once" =~ ^[01]$ ]]
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
    ps -eo pid=,ppid=,rss=,%cpu=,etimes= |
      awk -v root="$supervisor_pid" '
        {
          row_pid[NR] = $1;
          row_parent[NR] = $2;
          row_rss[NR] = $3;
          row_cpu[NR] = $4;
          row_elapsed[NR] = $5
        }
        END {
          in_tree[root] = 1;
          changed = 1;
          while (changed) {
            changed = 0;
            for (i = 1; i <= NR; i++) {
              if (in_tree[row_parent[i]] && !in_tree[row_pid[i]]) {
                in_tree[row_pid[i]] = 1;
                changed = 1
              }
            }
          }
          for (i = 1; i <= NR; i++) {
            if (in_tree[row_pid[i]] && row_rss[i] > maximum) {
              maximum = row_rss[i];
              pid = row_pid[i];
              cpu = row_cpu[i];
              elapsed = row_elapsed[i]
            }
          }
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
  [[ "$sample_once" == 1 ]] && break
  sleep "$sample_interval"
done
