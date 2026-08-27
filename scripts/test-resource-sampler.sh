#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test_dir=$(mktemp -d /tmp/candle-resource-sampler.XXXXXX)
memory_pid=
cleanup() {
  if [[ -n "$memory_pid" ]]; then
    kill "$memory_pid" 2>/dev/null || true
    wait "$memory_pid" 2>/dev/null || true
  fi
  find "$test_dir" -mindepth 1 -maxdepth 2 -type f -delete
  rmdir "$test_dir/checkpoints"
  rmdir "$test_dir"
}
trap cleanup EXIT

mkdir "$test_dir/checkpoints"
printf 'trace' >"$test_dir/trace.pft.bin"
python3 -c 'import time; memory = bytearray(20 * 1024 * 1024); time.sleep(30)' &
memory_pid=$!
for _ in $(seq 1 50); do
  memory_rss=$(ps -p "$memory_pid" -o rss= | tr -d ' ')
  [[ -n "$memory_rss" && "$memory_rss" -gt 10000 ]] && break
  sleep 0.1
done
[[ -n "$memory_rss" && "$memory_rss" -gt 10000 ]]

CANDLE_RESOURCE_SAMPLE_ONCE=1 \
  "$project_dir/scripts/sample-flyspeck-run.sh" \
    "$test_dir" "$test_dir/trace.pft.bin" "$$"

IFS=$'\t' read -r _ _ _ sampled_pid sampled_rss _ < <(
  tail -n 1 "$test_dir/resources.tsv"
)
[[ "$sampled_pid" == "$memory_pid" ]]
[[ "$sampled_rss" -gt 10000 ]]
printf 'PASS: resource sampler covers the full supervisor process tree\n'
