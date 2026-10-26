#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-historical-checked-sound-v679a
output=/project/flyspeck-candle-runs/v679b-fast-nl-tag9-residual-diagnostic-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=$project/tools/fast_nl_v679b_tag9_residual_diagnostic.ml
timeout_seconds=600
marker=CANDLE_FLYSPECK_V679B_TAG9_RESIDUAL_DIAGNOSTIC_OK

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
[[ -f $driver && ! -L $driver ]]
[[ -x $runtime/cake ]]
sha256sum -c "$base/checkpoint.sha256"
mapfile -t checkpoints < <(
  find "$base/checkpoint" -maxdepth 1 -type f -name 'ckpt_*.dmtcp' -print
)
[[ ${#checkpoints[@]} -eq 1 ]]

nonce=$(printf '%s\n%s\n' "$output" "$(sha256sum "$driver")" |
  sha256sum | awk '{print $1}')
parser=$(sed '/^#use /d' "$driver" |
  "$runtime/cake" --candle-parser-diagnostic-v1 "$nonce" 2>&1)
[[ $parser == \
  "CANDLE_CAMLPARSER_DIAGNOSTIC_V1"$'\t'"$nonce"$'\t'"OK" ]]

mkdir -p "$output/dmtcp-tmp"
ack="CANDLE_RESTORE_INPUT_ACK nonce=$nonce"
{
  printf 'print_endline "%s";;\n' "$ack"
  sed -n '1,$p' "$driver"
} >"$output/stdin.ml"

started=$(date +%s)
cd "$runtime"
set +e
env -i PATH=/project/bin:/usr/local/bin:/usr/bin:/bin LC_ALL=C \
  CML_HEAP_SIZE=32768 DMTCP_TMPDIR="$output/dmtcp-tmp" \
  timeout "$timeout_seconds" dmtcp_restart --new-coordinator --coord-port 0 \
    --port-file "$output/coord.port" "${checkpoints[0]}" \
    <"$output/stdin.ml" >"$output/runtime.log" 2>&1 &
runtime_pid=$!
set -e
printf '%s\n' "$runtime_pid" >"$output/runtime.pid"

status=1
for _ in $(seq 1 "$timeout_seconds"); do
  if rg -a -q 'ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory' \
       "$output/runtime.log"; then
    printf '%s\n' 'tag9 diagnostic observed a Candle error' >"$output/PROBE-FAILED"
    break
  fi
  ack_count=$(rg -a -Fxc "$ack" "$output/runtime.log" || true)
  marker_count=$(rg -a -Foc "$marker" "$output/runtime.log" || true)
  if [[ $ack_count -eq 1 && $marker_count -eq 1 ]]; then
    status=0
    break
  fi
  if ! kill -0 "$runtime_pid" 2>/dev/null; then
    printf '%s\n' 'tag9 diagnostic exited before completion' >"$output/PROBE-FAILED"
    break
  fi
  sleep 1
done

if [[ $status -ne 0 ]]; then
  [[ -f $output/PROBE-FAILED ]] ||
    printf '%s\n' 'tag9 diagnostic timed out' >"$output/PROBE-FAILED"
  exit 1
fi

port=$(<"$output/coord.port")
dmtcp_command --port "$port" -k >"$output/dmtcp-stop.log" 2>&1 || true
set +e
wait "$runtime_pid"
runtime_status=$?
set -e
elapsed=$(( $(date +%s) - started ))

[[ $(rg -a -Fxc "$ack" "$output/runtime.log" || true) -eq 1 ]]
[[ $(rg -a -Foc "$marker" "$output/runtime.log" || true) -eq 1 ]]
[[ $(rg -a -Foc 'CANDLE_FLYSPECK_V679B_TAG9_RESIDUAL goal=' \
       "$output/runtime.log" || true) -eq 1 ]]
sha256sum "$output/runtime.log" >"$output/runtime-log.sha256"
printf '%s\n' \
  'receipt_kind=development-fast-nl-v679b-tag9-residual-diagnostic-v1' \
  'release_evidence=false' \
  'status=0' \
  "base_checkpoint=${checkpoints[0]}" \
  "base_checkpoint_sha256=$(sha256sum "${checkpoints[0]}" | awk '{print $1}')" \
  "driver=$driver" \
  "driver_sha256=$(sha256sum "$driver" | awk '{print $1}')" \
  "fresh_ack=$ack" \
  "elapsed_seconds=$elapsed" \
  "runtime_exit_after_stop=$runtime_status" \
  "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >"$output/tag9-residual.receipt"
touch "$output/PROBE-PASSED"
