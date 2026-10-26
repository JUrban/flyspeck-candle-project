#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-direct-source-interface-v678
output=/project/flyspeck-candle-runs/v679-fast-nl-loaded-source-ledger-probe-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=$project/tools/fast_nl_v679_loaded_source_ledger_probe.ml
timeout_seconds=600
begin_marker=CANDLE_FLYSPECK_V679_LOADED_SOURCE_LEDGER_BEGIN
item_marker=CANDLE_FLYSPECK_V679_LOADED_SOURCE
end_marker=CANDLE_FLYSPECK_V679_LOADED_SOURCE_LEDGER_END

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

mkdir -p "$output/dmtcp-tmp"
driver_sha256=$(sha256sum "$driver" | awk '{print $1}')
nonce=$(printf '%s\n%s\n%s\n' "$output" "$driver_sha256" "$end_marker" |
  sha256sum | awk '{print $1}')
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
    printf '%s\n' 'ledger probe observed a Candle error' >"$output/PROBE-FAILED"
    break
  fi
  ack_count=$(rg -a -Fxc "$ack" "$output/runtime.log" || true)
  end_count=$(rg -a -Foc "$end_marker" "$output/runtime.log" || true)
  if [[ $ack_count -eq 1 && $end_count -eq 1 ]]; then
    status=0
    break
  fi
  if ! kill -0 "$runtime_pid" 2>/dev/null; then
    printf '%s\n' 'ledger probe runtime exited before completion' >"$output/PROBE-FAILED"
    break
  fi
  sleep 1
done

if [[ $status -ne 0 ]]; then
  [[ -f $output/PROBE-FAILED ]] ||
    printf '%s\n' 'ledger probe timed out before completion' >"$output/PROBE-FAILED"
  exit 1
fi

port=$(<"$output/coord.port")
dmtcp_command --port "$port" -k >"$output/dmtcp-stop.log" 2>&1 || true
set +e
wait "$runtime_pid"
runtime_status=$?
set -e
elapsed_seconds=$(( $(date +%s) - started ))

begin_line=$(rg -a -F "$begin_marker count=" "$output/runtime.log")
[[ $(printf '%s\n' "$begin_line" | wc -l) -eq 1 ]]
loaded_source_count=${begin_line##*count=}
[[ $loaded_source_count =~ ^[1-9][0-9]*$ ]]
observed_item_count=$(rg -a -Foc "${item_marker} identity=" "$output/runtime.log" || true)
[[ $observed_item_count -eq $loaded_source_count ]]
[[ $(rg -a -Fxc "$ack" "$output/runtime.log" || true) -eq 1 ]]
[[ $(rg -a -Foc "$end_marker" "$output/runtime.log" || true) -eq 1 ]]

sha256sum "$output/runtime.log" >"$output/runtime-log.sha256"
printf '%s\n' \
  'receipt_kind=development-fast-nl-loaded-source-ledger-probe-v1' \
  'release_evidence=false' \
  'status=0' \
  "base_checkpoint=${checkpoints[0]}" \
  "base_checkpoint_sha256=$(sha256sum "${checkpoints[0]}" | awk '{print $1}')" \
  "driver=$driver" \
  "driver_sha256=$driver_sha256" \
  "fresh_ack=$ack" \
  "loaded_source_count=$loaded_source_count" \
  "elapsed_seconds=$elapsed_seconds" \
  "runtime_exit_after_stop=$runtime_status" \
  "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >"$output/loaded-source-ledger.receipt"
touch "$output/PROBE-PASSED"
