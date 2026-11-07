#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'usage: %s OUTPUT_DIR\n' "$0" >&2
  exit 2
fi

output=$1
project=/project/flyspeck-candle-project
stock_base=/project/flyspeck-candle-runs/v521-direct-case16594-handoff-support-checkpoint-dev-001
stock_source=/project/worktrees/candle-nl-g7-case16594-v1/candle/benchmark_cv_compute_analytic_expr_case16594_matched_stock_route.ml
stock_driver=/project/worktrees/candle-nl-g7-case16594-v1/candle/benchmark_cv_compute_analytic_expr_case16594_matched_stock_route_run.ml
stock_runner=$project/scripts/run-fast-nl-restored-source-bodies-probe-v1.sh
stock_marker=CANDLE_CV_CASE16594_MATCHED_STOCK_ROUTE_OK
fast_binary=/project/flyspeck-candle-runs/v3902-nl-g6-direct-integrated-final-oracle-dev-001/checker
fast_certificate=/project/flyspeck-candle-runs/v3865-nl-case16594-plus-one-radii-fast-probe-dev-001/source-tight-all-radii-plus-one-recaptured.bin
fast_cells=/project/flyspeck-candle-runs/v3893-nl-g6-complete875-payload-dev-001/packed-cells-pad1-source-outer-control.cvdata
fast_tokens=/project/flyspeck-candle-runs/v3893-nl-g6-complete875-payload-dev-001/topology-tokens.cvdata
fast_jobs=/project/flyspeck-candle-runs/v3893-nl-g6-complete875-payload-dev-001/encoded-jobs-pad1-source-outer-control.cvdata
benchmark_cpu=${CASE16594_MATCHED_CPU:-110}
max_initial_load=${CASE16594_MATCHED_MAX_INITIAL_LOAD:-12}
min_available_kib=${CASE16594_MATCHED_MIN_AVAILABLE_KIB:-104857600}

[[ ! -e $output ]]
[[ -f $stock_base/CHECKPOINT-READY ]]
[[ ! -f $stock_base/CHECKPOINT-FAILED ]]
[[ -f $stock_source && -f $stock_driver && -x $stock_runner && -x $fast_binary ]]
[[ $benchmark_cpu =~ ^[0-9]+$ ]]
(( benchmark_cpu < $(nproc) ))

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
verify_hash a68b51ad931422bdd6ab5058a7c7db4d62b862dcd2f6635c72dfe02872d9d08f "$fast_binary"
verify_hash c774cb7cf6894fba1f7934e80647383deba6e23c8773933f89fd2efcb0888fcb "$fast_certificate"
verify_hash 6477d8364bc0c5e4938456e267e7db03fd5daed9c15965a57fd199e26d538e3a "$fast_cells"
verify_hash e9ccb034752c508948229e74865eecf1b54dafdbef0c223580522ce3e997a0ab "$fast_tokens"
verify_hash 2a7dec313b23c5dc1804399f39ab3642c7a98d0eb34dd8d83f16029735aa6a18 "$fast_jobs"
sha256sum -c "$stock_base/checkpoint.sha256"

mkdir -p "$output"

snapshot() {
  local label=$1
  local destination=$2
  {
    printf 'label=%s\n' "$label"
    printf 'utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'cpu=%s\n' "$benchmark_cpu"
    printf 'loadavg='
    cat /proc/loadavg
    uptime
    free -k
    vmstat 1 2
    ps -eo pid,ppid,etimes,psr,stat,%cpu,%mem,rss,comm,args --sort=-rss | head -40
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

watch_stock_phases() {
  local timed_pid=$1
  local run=$2
  local destination=$3
  local runtime_pid marker
  printf 'utc_nanoseconds\tprocess_tree_cpu_ticks\tmarker\n' >"$destination"
  while [[ ! -f $run/runtime.log || ! -f $run/runtime.pid ]]; do
    kill -0 "$timed_pid" 2>/dev/null || return 0
    sleep 0.05
  done
  runtime_pid=$(<"$run/runtime.pid")
  tail --pid="$timed_pid" -n +1 -F "$run/runtime.log" 2>/dev/null |
    while IFS= read -r marker; do
      case $marker in
        *CANDLE_CASE16594_MATCHED_STOCK_PHASE*)
          printf '%s\t%s\t%s\n' \
            "$(date +%s%N)" "$(tree_cpu_ticks "$runtime_pid")" "$marker" \
            >>"$destination"
          ;;
      esac
    done
}

run_stock() {
  local index=$1
  local run=$output/stock-$index
  local timed_pid watcher_pid timed_status
  snapshot "stock-$index-start" "$output/stock-$index-start.state"
  set +e
  /usr/bin/time -v -o "$output/stock-$index.time" \
    taskset -c "$benchmark_cpu" \
    env FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=1200 \
      "$stock_runner" "$stock_base" "$run" "$stock_marker" \
      "$stock_source" "$stock_driver" \
      >"$output/stock-$index.stdout" \
      2>"$output/stock-$index.stderr" &
  timed_pid=$!
  watch_stock_phases "$timed_pid" "$run" "$output/stock-$index.phases.tsv" &
  watcher_pid=$!
  wait "$timed_pid"
  timed_status=$?
  wait "$watcher_pid" || true
  set -e
  [[ $timed_status -eq 0 ]]
  [[ -f $run/PROBE-PASSED ]]
  [[ $(rg -a -Foc "$stock_marker" "$run/runtime.log") -eq 1 ]]
  snapshot "stock-$index-end" "$output/stock-$index-end.state"
}

run_fast() {
  local index=$1
  snapshot "fast-$index-start" "$output/fast-$index-start.state"
  /usr/bin/time -v -o "$output/fast-$index.time" \
    taskset -c "$benchmark_cpu" \
    timeout --signal=TERM --kill-after=10s 600s \
    env CML_STACK_SIZE=1000 CML_HEAP_SIZE=6000 \
      "$fast_binary" positive "$fast_certificate" "$fast_cells" \
      "$fast_tokens" "$fast_jobs" \
      >"$output/fast-$index.stdout" \
      2>"$output/fast-$index.stderr"
  [[ $(<"$output/fast-$index.stdout") == accepted ]]
  snapshot "fast-$index-end" "$output/fast-$index-end.state"
}

for index in 1 2 3; do
  run_stock "$index"
  run_fast "$index"
done

{
  printf '%s\n' \
    'receipt_kind=case16594-matched-stock-fast-benchmark-v1' \
    'release_evidence=false' \
    'runs_per_route=3' \
    'execution_order=stock1-fast1-stock2-fast2-stock3-fast3' \
    "pinned_cpu=$benchmark_cpu" \
    "initial_load1=$initial_load" \
    "initial_mem_available_kib=$available_kib" \
    "initial_swap_in_kib_per_second=$swap_in" \
    "initial_swap_out_kib_per_second=$swap_out" \
    "clock_ticks_per_second=$(getconf CLK_TCK)" \
    "stock_base=$stock_base" \
    "stock_checkpoint_sha256=$(awk '{print $1}' "$stock_base/checkpoint.sha256")" \
    "stock_source=$stock_source" \
    "stock_source_sha256=$(sha256sum "$stock_source" | awk '{print $1}')" \
    "stock_driver=$stock_driver" \
    "stock_driver_sha256=$(sha256sum "$stock_driver" | awk '{print $1}')" \
    "fast_binary_sha256=$(sha256sum "$fast_binary" | awk '{print $1}')" \
    "fast_certificate_sha256=$(sha256sum "$fast_certificate" | awk '{print $1}')" \
    "fast_cells_sha256=$(sha256sum "$fast_cells" | awk '{print $1}')" \
    "fast_tokens_sha256=$(sha256sum "$fast_tokens" | awk '{print $1}')" \
    "fast_jobs_sha256=$(sha256sum "$fast_jobs" | awk '{print $1}')" \
    'fast_geometry=source-rounded-radius-padding-one' \
    "completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$output/benchmark.receipt"

touch "$output/BENCHMARK-PASSED"
