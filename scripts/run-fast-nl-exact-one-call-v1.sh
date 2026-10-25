#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'usage: %s OUTPUT_BASENAME\n' "$0" >&2
  exit 2
fi

case $1 in
  theorem|theorem-repeat) ;;
  *) printf 'unsupported output basename: %s\n' "$1" >&2; exit 2 ;;
esac

run=${FAST_NL_RUN_DIR:-/project/flyspeck-candle-runs/v658-fast-nl-compiler64-final-stage-dev-001}
fixture=/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001
base_dir=$run/postsupport
output_dir=$run/$1
driver=$fixture/exact-one-call.ml
dev_runtime=${FAST_NL_DEV_RUNTIME:-/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-aa7ffbc-0f9690d-bc47e65-attempt-001}
expected_marker=CANDLE_CV_CASE10173_HISTORICAL_REGISTERED_FULL_CALL_ORIGINAL_PROVE_TEST_OK
numerical_marker=CANDLE_REGISTERED_FULL_CALL_REGISTERED_NUMERICAL_END
fast_numerical_max_seconds=120
numerical_watchdog_seconds=180
call_timeout_seconds=${FAST_NL_CALL_TIMEOUT_SECONDS:-21600}

[[ -f $base_dir/CHECKPOINT-READY ]]
[[ ! -f $base_dir/CHECKPOINT-FAILED ]]
[[ ! -e $output_dir ]]
[[ -x $dev_runtime/cake ]]
[[ $call_timeout_seconds =~ ^[1-9][0-9]*$ ]]
mapfile -t checkpoints < <(
  find "$base_dir/checkpoint" -maxdepth 1 -type f -name 'ckpt_*.dmtcp' -print
)
[[ ${#checkpoints[@]} -eq 1 ]]
sha256sum -c "$base_dir/checkpoint.sha256"
mkdir -p "$output_dir/dmtcp-tmp"
driver_sha=$(sha256sum "$driver" | awk '{print $1}')
nonce=$(printf '%s\n%s\n%s\n' "$output_dir" "$driver_sha" "$expected_marker" |
  sha256sum | awk '{print $1}')
ack="CANDLE_RESTORE_INPUT_ACK nonce=$nonce"
{
  printf 'print_endline "%s";;\n' "$ack"
  printf '#use "%s";;\n' "$driver"
} >"$output_dir/stdin.ml"

cd "$dev_runtime"
set +e
setsid /usr/bin/time -v -o "$output_dir/time.log" \
  env -i PATH=/project/bin:/usr/local/bin:/usr/bin:/bin LC_ALL=C \
    CML_HEAP_SIZE=32768 DMTCP_TMPDIR="$output_dir/dmtcp-tmp" \
    timeout "$call_timeout_seconds" dmtcp_restart --new-coordinator --coord-port 0 \
      --port-file "$output_dir/coord.port" "${checkpoints[0]}" \
      <"$output_dir/stdin.ml" >"$output_dir/runtime.log" 2>&1 &
launcher_pid=$!
numerical_watchdog_triggered=0
numerical_observed_at=
while kill -0 "$launcher_pid" 2>/dev/null; do
  if rg -a -Fq "CANDLE_REGISTERED_FULL_CALL_REGISTERED_NUMERICAL_BEGIN" \
       "$output_dir/runtime.log" &&
     ! rg -a -Fq "CANDLE_REGISTERED_FULL_CALL_REGISTERED_NUMERICAL_END" \
       "$output_dir/runtime.log"
  then
    if [[ -z $numerical_observed_at ]]; then
      numerical_observed_at=$(date +%s)
    elif (( $(date +%s) - numerical_observed_at >= numerical_watchdog_seconds )); then
      numerical_watchdog_triggered=1
      kill -TERM -- "-$launcher_pid" 2>/dev/null || true
      sleep 2
      kill -KILL -- "-$launcher_pid" 2>/dev/null || true
      break
    fi
  fi
  sleep 1
done
wait "$launcher_pid"
runtime_status=$?
set -e

ack_count=$(rg -a -Fxc "$ack" "$output_dir/runtime.log" || true)
marker_count=$(rg -a -Fc "$expected_marker" "$output_dir/runtime.log" || true)
failure_count=$(rg -a -c '^(EXCEPTION:|ERROR:)|Parsing failed|Program exited|Fatal error|Out of memory' \
  "$output_dir/runtime.log" || true)
numerical_timing_count=$(rg -a -c \
  "^${numerical_marker} elapsed_seconds=[0-9]+([.][0-9]*)?([eE][+-]?[0-9]+)?$" \
  "$output_dir/runtime.log" || true)
numerical_seconds=$(sed -n \
  "s/^${numerical_marker} elapsed_seconds=//p" \
  "$output_dir/runtime.log" | tail -1)
fast_timing_ok=0
if [[ $numerical_timing_count -eq 1 ]] &&
   awk -v seconds="$numerical_seconds" -v limit="$fast_numerical_max_seconds" \
     'BEGIN { exit !(seconds > 0 && seconds <= limit) }'
then
  fast_timing_ok=1
fi
status=$runtime_status
if [[ $ack_count -ne 1 || $marker_count -ne 1 || $failure_count -ne 0 ||
      $numerical_watchdog_triggered -ne 0 || $fast_timing_ok -ne 1 ]]; then
  status=1
fi
printf '%s\n' "$status" >"$output_dir/exit.status"
printf 'runtime_status=%s\nack_count=%s\nmarker_count=%s\nfailure_count=%s\nnumerical_timing_count=%s\nnumerical_seconds=%s\nfast_numerical_max_seconds=%s\nnumerical_watchdog_seconds=%s\nnumerical_watchdog_triggered=%s\nfast_timing_ok=%s\n' \
  "$runtime_status" "$ack_count" "$marker_count" "$failure_count" \
  "$numerical_timing_count" "$numerical_seconds" \
  "$fast_numerical_max_seconds" "$numerical_watchdog_seconds" \
  "$numerical_watchdog_triggered" "$fast_timing_ok" \
  >"$output_dir/result-validation.txt"
sha256sum "$driver" "$output_dir/stdin.ml" "$output_dir/runtime.log" \
  "$dev_runtime/cake" "$dev_runtime/DEVELOPMENT-NONPROMOTABLE.json" \
  "$base_dir/checkpoint.receipt" >"$output_dir/result-files.sha256"
exit "$status"
