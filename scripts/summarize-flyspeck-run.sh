#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'usage: %s <state-directory>\n' "$0" >&2
  exit 2
fi

state_dir=$(realpath -m -- "$1")
sample_file="$state_dir/resources.tsv"
status_file="$state_dir/status.tsv"
config_file="$state_dir/run.conf"

[[ -s "$sample_file" && -s "$status_file" && -s "$config_file" ]]
output=$(sed -n 's/^output=//p' "$config_file")
[[ -n "$output" && -f "$output" ]]

read -r first_utc last_utc samples max_rss max_cpu max_trace max_checkpoint < <(
  awk -F '\t' '
    NR == 2 { first = $1 }
    NR > 1 {
      last = $1;
      samples += 1;
      if ($5 + 0 > rss + 0) rss = $5;
      if ($6 + 0 > cpu + 0) cpu = $6;
      if ($8 + 0 > trace + 0) trace = $8;
      if ($9 + 0 > checkpoint + 0) checkpoint = $9
    }
    END {
      if (samples == 0) exit 1;
      print first, last, samples, rss, cpu, trace, checkpoint
    }' "$sample_file"
)

first_epoch=$(date -u -d "$first_utc" +%s)
last_epoch=$(date -u -d "$last_utc" +%s)
span_seconds=$((last_epoch - first_epoch))
output_sha=$(sha256sum "$output" | cut -d' ' -f1)

printf 'sample_start_utc=%s\n' "$first_utc"
printf 'sample_end_utc=%s\n' "$last_utc"
printf 'sample_span_seconds=%s\n' "$span_seconds"
printf 'samples=%s\n' "$samples"
printf 'peak_run_process_rss_kib=%s\n' "$max_rss"
printf 'peak_process_cpu_percent=%s\n' "$max_cpu"
printf 'peak_trace_bytes=%s\n' "$max_trace"
printf 'peak_checkpoint_bytes=%s\n' "$max_checkpoint"
printf 'final_trace_bytes=%s\n' "$(stat -c '%s' "$output")"
printf 'final_trace_sha256=%s\n' "$output_sha"
printf 'final_status=%s\n' "$(tr '\t' ' ' <"$status_file")"
