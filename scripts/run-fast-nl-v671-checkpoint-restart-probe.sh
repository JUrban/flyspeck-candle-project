#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/posttaylor-interval-v671
output=/project/flyspeck-candle-runs/v671-fast-nl-taylor-interval-restart-probe-dev-003
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
marker=CANDLE_FLYSPECK_V671_RESTART_PROBE_OK
timeout_seconds=600

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
[[ -x $runtime/cake ]]
sha256sum -c "$base/checkpoint.sha256"
mapfile -t checkpoints < <(
  find "$base/checkpoint" -maxdepth 1 -type f -name 'ckpt_*.dmtcp' -print
)
[[ ${#checkpoints[@]} -eq 1 ]]

mkdir -p "$output/dmtcp-tmp"
mkfifo "$output/input.fifo" "$output/output.fifo"
tail -f /dev/null >"$output/input.fifo" &
keeper_pid=$!
tee "$output/runtime.log" <"$output/output.fifo" >/dev/null &
reader_pid=$!
runtime_pid=
cleanup() {
  kill "$keeper_pid" "$reader_pid" 2>/dev/null || true
  if [[ -n $runtime_pid ]]; then kill "$runtime_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT

checkpoint_sha=$(sha256sum "${checkpoints[0]}" | awk '{print $1}')
nonce=$(printf '%s\n%s\n' "$checkpoint_sha" "$output" | sha256sum | awk '{print $1}')
ack="CANDLE_RESTORE_INPUT_ACK nonce=$nonce"
{
  printf 'print_endline "%s";;\n' "$ack"
  printf 'print_endline "%s";;\n' "$marker"
} >"$output/input.fifo" &
writer_pid=$!

started=$(date +%s)
cd "$runtime"
env -i PATH=/project/bin:/usr/local/bin:/usr/bin:/bin LC_ALL=C \
  CML_HEAP_SIZE=32768 DMTCP_TMPDIR="$output/dmtcp-tmp" \
  timeout "$timeout_seconds" dmtcp_restart --new-coordinator --coord-port 0 \
    --port-file "$output/coord.port" "${checkpoints[0]}" \
    <"$output/input.fifo" >"$output/output.fifo" 2>&1 &
runtime_pid=$!
printf '%s\n' "$runtime_pid" >"$output/runtime.pid"
wait "$writer_pid"

status=1
for _ in $(seq 1 "$timeout_seconds"); do
  if rg -a -q 'ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory' \
       "$output/runtime.log"; then
    printf '%s\n' 'restart probe observed a Candle error' >"$output/PROBE-FAILED"
    break
  fi
  ack_count=$(rg -a -Fxc "$ack" "$output/runtime.log" || true)
  marker_count=$(rg -a -Foc "$marker" "$output/runtime.log" || true)
  if [[ $ack_count -eq 1 && $marker_count -eq 1 ]]; then
    status=0
    break
  fi
  if ! kill -0 "$runtime_pid" 2>/dev/null; then
    printf '%s\n' 'restart probe runtime exited before fresh markers' >"$output/PROBE-FAILED"
    break
  fi
  sleep 1
done

if [[ $status -ne 0 ]]; then
  [[ -f $output/PROBE-FAILED ]] ||
    printf '%s\n' 'restart probe timed out before fresh markers' >"$output/PROBE-FAILED"
  exit 1
fi

port=$(<"$output/coord.port")
dmtcp_command --port "$port" -k >"$output/dmtcp-stop.log" 2>&1 || true
set +e
wait "$runtime_pid"
runtime_status=$?
set -e
runtime_pid=
wait "$reader_pid" || true
reader_pid=
kill "$keeper_pid" 2>/dev/null || true
keeper_pid=
elapsed=$(( $(date +%s) - started ))

sha256sum "$output/runtime.log" >"$output/runtime-log.sha256"
printf '%s\n' \
  'receipt_kind=development-fast-nl-v671-checkpoint-restart-probe-v1' \
  'release_evidence=false' \
  "base_checkpoint=${checkpoints[0]}" \
  "base_checkpoint_sha256=$checkpoint_sha" \
  "fresh_ack=$ack" \
  "expected_marker=$marker" \
  "elapsed_seconds=$elapsed" \
  "runtime_exit_after_stop=$runtime_status" \
  "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >"$output/restart-probe.receipt"
touch "$output/PROBE-PASSED"
