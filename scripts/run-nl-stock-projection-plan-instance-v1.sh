#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  printf 'usage: %s SOURCE_ID PARAMETER_INDEX PLAN_SOURCE OUTPUT_DIR\n' "$0" >&2
  exit 2
fi

source_id=$1
parameter_index=$2
plan_source=$3
output=$4
project=/project/flyspeck-candle-project
candle=/project/worktrees/candle-nl-g7-case16594-v1
compatibility=$candle/candle/cv_compute_flyspeck_direct_source_compat.ml
base=${NL_STOCK_PROJECTION_PLAN_BASE:-/project/flyspeck-candle-runs/nl-stock-projection-hminus-setup-checkpoint-v1-dev-005}
runner=$project/scripts/run-fast-nl-restored-source-bodies-probe-v1.sh
generator=$project/scripts/generate-nl-stock-projection-plan-probe.py
marker=CANDLE_NL_STOCK_PROJECTION_PLAN_OK
plan_cpu=${NL_STOCK_PROJECTION_PLAN_CPU:-111}
max_initial_load=${NL_STOCK_PROJECTION_PLAN_MAX_INITIAL_LOAD:-64}
min_available_kib=${NL_STOCK_PROJECTION_PLAN_MIN_AVAILABLE_KIB:-104857600}

[[ $parameter_index =~ ^[0-9]+$ ]]
[[ $plan_source = /* ]]
[[ -f $plan_source ]]
[[ ! -e $output ]]
[[ -x $runner && -x $generator ]]
[[ -f $compatibility ]]
[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ $plan_cpu =~ ^[0-9]+$ ]]
(( plan_cpu < $(nproc) ))

if [[ $(git -C "$candle" rev-parse HEAD) != \
      aab1b8e5a4ba7dff2123d4905c5543bba1afae57 ]]; then
  printf '%s\n' 'Candle worktree head drift' >&2
  exit 1
fi
if [[ -n $(git -C "$candle" status --porcelain) ]]; then
  printf '%s\n' 'Candle worktree is dirty' >&2
  exit 1
fi

# Recreate the generated source from its logical identity and require exact
# byte equality.  This prevents a hand-edited instance from entering a plan
# checkpoint merely because its provenance comment still looks plausible.
comparison=$(mktemp -d)
cleanup() {
  rm -r "$comparison"
}
trap cleanup EXIT
"$generator" --source-id "$source_id" --parameter-index "$parameter_index" \
  --output "$comparison/plan_probe.ml" >"$comparison/generator.log"
cmp "$comparison/plan_probe.ml" "$plan_source"

initial_load=$(awk '{print $1}' /proc/loadavg)
available_kib=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
swap_sample=$(vmstat 1 2 | tail -1)
swap_in=$(awk '{print $7}' <<<"$swap_sample")
swap_out=$(awk '{print $8}' <<<"$swap_sample")
if ! awk -v observed="$initial_load" -v cap="$max_initial_load" \
    'BEGIN {exit !(observed <= cap)}'; then
  printf 'resource gate: load1=%s exceeds cap=%s\n' \
    "$initial_load" "$max_initial_load" >&2
  exit 1
fi
if (( available_kib < min_available_kib )); then
  printf 'resource gate: MemAvailable=%s KiB below floor=%s KiB\n' \
    "$available_kib" "$min_available_kib" >&2
  exit 1
fi
if [[ $swap_in != 0 || $swap_out != 0 ]]; then
  printf 'resource gate: active swapping si=%s so=%s\n' \
    "$swap_in" "$swap_out" >&2
  exit 1
fi
if pgrep -af '(^|/)(cake|checker|mtcp_restart)( |$)' >/dev/null; then
  printf '%s\n' 'resource gate: another Cake/checker process is active' >&2
  pgrep -af '(^|/)(cake|checker|mtcp_restart)( |$)' >&2 || true
  exit 1
fi

taskset -c "$plan_cpu" \
  env FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=1200 \
      FAST_NL_SOURCE_BODIES_CHECKPOINT_AFTER_SUCCESS=1 \
    "$runner" "$base" "$output" "$marker" \
    "$compatibility" "$plan_source"

[[ -f $output/PROBE-PASSED ]]
[[ -f $output/CHECKPOINT-READY ]]
[[ ! -f $output/PROBE-FAILED ]]
[[ $(rg -a -Foc "$marker" "$output/runtime.log") -eq 1 ]]
[[ $(rg -a -Foc \
  "source=$source_id parameter_index=$parameter_index" \
  "$output/runtime.log") -eq 1 ]]
[[ $(rg -a -c \
  'ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory' \
  "$output/runtime.log" || true) -eq 0 ]]

printf '%s\n' \
  'receipt_kind=nl-stock-projection-plan-instance-v1' \
  'release_evidence=false' \
  "source_id=$source_id" \
  "parameter_index=$parameter_index" \
  "pinned_cpu=$plan_cpu" \
  "initial_load1=$initial_load" \
  "initial_mem_available_kib=$available_kib" \
  "initial_swap_in_kib_per_second=$swap_in" \
  "initial_swap_out_kib_per_second=$swap_out" \
  "base_checkpoint_sha256=$(awk '{print $1}' "$base/checkpoint.sha256")" \
  "compatibility_sha256=$(sha256sum "$compatibility" | awk '{print $1}')" \
  "plan_source_sha256=$(sha256sum "$plan_source" | awk '{print $1}')" \
  "checkpoint_sha256=$(awk '{print $1}' "$output/checkpoint.sha256")" \
  "completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >"$output/plan-instance.receipt"

touch "$output/PLAN-INSTANCE-PASSED"
