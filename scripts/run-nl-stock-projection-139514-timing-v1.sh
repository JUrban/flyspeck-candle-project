#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'usage: %s OUTPUT_DIR\n' "$0" >&2
  exit 2
fi

output=$1
project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/nl-stock-projection-plan-139514-checkpoint-v1-dev-001
runner=$project/scripts/run-fast-nl-restored-source-bodies-probe-v1.sh
cells=$project/tools/nl_stock_projection_cells_139514.ml
plan=$project/tools/nl_stock_projection_repaired_plan_139514.ml
complete=$project/tools/nl_stock_projection_complete_139514.ml
marker=CANDLE_NL_STOCK_PROJECTION_COMPLETE_OK
timing_cpu=${NL_STOCK_PROJECTION_TIMING_CPU:-110}
max_initial_load=${NL_STOCK_PROJECTION_TIMING_MAX_INITIAL_LOAD:-12}
min_available_kib=${NL_STOCK_PROJECTION_TIMING_MIN_AVAILABLE_KIB:-104857600}

[[ ! -e $output ]]
[[ -x $runner ]]
[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ $timing_cpu =~ ^[0-9]+$ ]]
(( timing_cpu < $(nproc) ))

verify_hash() {
  local expected=$1
  local path=$2
  local actual
  actual=$(sha256sum "$path" | awk '{print $1}')
  if [[ $actual != "$expected" ]]; then
    printf 'identity mismatch: %s expected=%s actual=%s\n' \
      "$path" "$expected" "$actual" >&2
    exit 1
  fi
}

verify_hash \
  791e442eb88580641efad2a92c7f8fc49c487c3d58fb150e89d2fd0b1274eb85 \
  "$cells"
verify_hash \
  95d67c9d7778960026d35379e1b8b7108f1e993db7b93f6156ae1ccd7998c871 \
  "$plan"
verify_hash \
  919116e7bf93f2a7e0f546cb42e7172fd6182d0b22a8420d93407c84acb6f4be \
  "$complete"

initial_load=$(awk '{print $1}' /proc/loadavg)
available_kib=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
swap_sample=$(vmstat 1 2 | tail -1)
swap_in=$(awk '{print $7}' <<<"$swap_sample")
swap_out=$(awk '{print $8}' <<<"$swap_sample")
if ! awk -v observed="$initial_load" -v cap="$max_initial_load" \
    'BEGIN {exit !(observed <= cap)}'; then
  printf 'quiet-host gate: load1=%s exceeds cap=%s\n' \
    "$initial_load" "$max_initial_load" >&2
  exit 1
fi
if (( available_kib < min_available_kib )); then
  printf 'quiet-host gate: MemAvailable=%s KiB below floor=%s KiB\n' \
    "$available_kib" "$min_available_kib" >&2
  exit 1
fi
if [[ $swap_in != 0 || $swap_out != 0 ]]; then
  printf 'quiet-host gate: active swapping si=%s so=%s\n' \
    "$swap_in" "$swap_out" >&2
  exit 1
fi
if pgrep -af '(^|/)(cake|checker|mtcp_restart)( |$)' >/dev/null; then
  printf '%s\n' 'quiet-host gate: another Cake/checker process is active' >&2
  pgrep -af '(^|/)(cake|checker|mtcp_restart)( |$)' >&2 || true
  exit 1
fi
sha256sum -c "$base/checkpoint.sha256"

mkdir -p "$output"

snapshot() {
  local label=$1
  local destination=$2
  {
    printf 'label=%s\n' "$label"
    printf 'utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'cpu=%s\n' "$timing_cpu"
    printf 'loadavg='
    cat /proc/loadavg
    uptime
    free -k
    vmstat 1 2
    ps -eo pid,ppid,etimes,psr,stat,%cpu,%mem,rss,comm,args --sort=-rss |
      head -40
  } >"$destination"
}

tree_cpu_ticks() {
  local root=$1
  local frontier=($root)
  local all=()
  local parent child stat ticks=0
  while (( ${#frontier[@]} > 0 )); do
    parent=${frontier[0]}
    frontier=("${frontier[@]:1}")
    [[ -r /proc/$parent/stat ]] || continue
    all+=("$parent")
    while read -r child; do
      [[ -n $child ]] && frontier+=("$child")
    done < <(ps -o pid= --ppid "$parent" 2>/dev/null || true)
  done
  for parent in "${all[@]}"; do
    [[ -r /proc/$parent/stat ]] || continue
    stat=$(<"/proc/$parent/stat")
    ticks=$((ticks + $(awk '{print $14 + $15}' <<<"$stat")))
  done
  printf '%s\n' "$ticks"
}

watch_phases() {
  local timed_pid=$1
  local run=$2
  local destination=$3
  local runtime_pid line
  printf 'utc_nanoseconds\tprocess_tree_cpu_ticks\tmarker\n' >"$destination"
  while [[ ! -f $run/runtime.log || ! -f $run/runtime.pid ]]; do
    kill -0 "$timed_pid" 2>/dev/null || return 0
    sleep 0.05
  done
  runtime_pid=$(<"$run/runtime.pid")
  tail --pid="$timed_pid" -n +1 -F "$run/runtime.log" 2>/dev/null |
    while IFS= read -r line; do
      case $line in
        *CANDLE_RESTORE_INPUT_ACK*|\
        *CANDLE_NL_STOCK_PROJECTION_CELLS*|\
        *CANDLE_NL_STOCK_PROJECTION_REPAIRED_PLAN_OK*|\
        *CANDLE_NL_STOCK_PROJECTION_COMPLETE*|\
        *CANDLE_CERT_PROFILE*phase=variable-complete-*)
          printf '%s\t%s\t%s\n' \
            "$(date +%s%N)" "$(tree_cpu_ticks "$runtime_pid")" "$line" \
            >>"$destination"
          ;;
      esac
    done
}

run=$output/stock
snapshot start "$output/start.state"
set +e
/usr/bin/time -v -o "$output/stock.time" \
  taskset -c "$timing_cpu" \
  env FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=1200 \
    "$runner" "$base" "$run" "$marker" \
    "$cells" "$plan" "$complete" \
    >"$output/stock.stdout" 2>"$output/stock.stderr" &
timed_pid=$!
watch_phases "$timed_pid" "$run" "$output/stock.phases.tsv" &
watcher_pid=$!
wait "$timed_pid"
timed_status=$?
wait "$watcher_pid" || true
set -e
[[ $timed_status -eq 0 ]]
[[ -f $run/PROBE-PASSED ]]
[[ $(rg -a -Foc "$marker" "$run/runtime.log") -eq 1 ]]
[[ $(rg -a -Foc \
  'theorem_digest=ad47952de83b1c56748556d69c4e1cb0' \
  "$run/runtime.log") -eq 1 ]]
[[ $(rg -a -c \
  'ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory' \
  "$run/runtime.log" || true) -eq 0 ]]
snapshot end "$output/end.state"

printf '%s\n' \
  'receipt_kind=nl-stock-projection-139514-timing-v1' \
  'release_evidence=false' \
  'source_id=prep-1395142356' \
  'parameter_index=3' \
  'original_cells=521' \
  'repaired_cells=534' \
  'token_items=1067' \
  "pinned_cpu=$timing_cpu" \
  "clock_ticks_per_second=$(getconf CLK_TCK)" \
  "initial_load1=$initial_load" \
  "initial_mem_available_kib=$available_kib" \
  "initial_swap_in_kib_per_second=$swap_in" \
  "initial_swap_out_kib_per_second=$swap_out" \
  "base_checkpoint_sha256=$(awk '{print $1}' "$base/checkpoint.sha256")" \
  "cells_sha256=$(sha256sum "$cells" | awk '{print $1}')" \
  "plan_sha256=$(sha256sum "$plan" | awk '{print $1}')" \
  "complete_sha256=$(sha256sum "$complete" | awk '{print $1}')" \
  'theorem_digest=ad47952de83b1c56748556d69c4e1cb0' \
  "completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >"$output/timing.receipt"

touch "$output/TIMING-PASSED"
