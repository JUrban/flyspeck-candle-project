#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test_dir=$(mktemp -d /tmp/candle-resource-summary.XXXXXX)
cleanup() {
  find "$test_dir" -mindepth 1 -maxdepth 1 -type f -delete
  rmdir "$test_dir"
}
trap cleanup EXIT

output="$test_dir/trace.pft.bin"
printf 'trace' >"$output"
printf 'output=%s\n' "$output" >"$test_dir/run.conf"
printf 'complete\t2\tfull\t5\t7\t1\t2\t3\n' >"$test_dir/status.tsv"
{
  printf 'utc\tphase\tindex\tpid\trss_kib\tcpu_percent\tprocess_elapsed_s\ttrace_bytes\tcheckpoint_bytes\n'
  printf '2026-08-27T00:00:00Z\tinitializing\t0\t1\t10\t50.0\t1\t2\t30\n'
  printf '2026-08-27T00:00:10Z\tcomplete\t2\t1\t20\t99.0\t11\t5\t0\n'
} >"$test_dir/resources.tsv"

summary=$(
  "$project_dir/scripts/summarize-flyspeck-run.sh" "$test_dir"
)
rg -q '^sample_span_seconds=10$' <<<"$summary"
rg -q '^samples=2$' <<<"$summary"
rg -q '^peak_run_process_rss_kib=20$' <<<"$summary"
rg -q '^peak_process_cpu_percent=99.0$' <<<"$summary"
rg -q '^peak_trace_bytes=5$' <<<"$summary"
rg -q '^peak_checkpoint_bytes=30$' <<<"$summary"
rg -q '^final_trace_bytes=5$' <<<"$summary"
rg -q '^final_status=complete 2 full 5 7 1 2 3$' <<<"$summary"
printf 'PASS: resource summary\n'
