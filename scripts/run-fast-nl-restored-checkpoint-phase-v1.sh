#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  printf 'usage: %s BASE_DIR OUTPUT_DIR DRIVER EXPECTED_MARKER RECEIPT_KIND\n' "$0" >&2
  exit 2
fi

base_dir=$1
output_dir=$2
driver=$3
expected_marker=$4
receipt_kind=$5
dev_runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-aa7ffbc-0f9690d-bc47e65-attempt-001

[[ -f $base_dir/CHECKPOINT-READY ]]
[[ ! -f $base_dir/CHECKPOINT-FAILED ]]
[[ ! -e $output_dir ]]
[[ -f $driver ]]
[[ -x $dev_runtime/cake ]]
mapfile -t checkpoints < <(
  find "$base_dir/checkpoint" -maxdepth 1 -type f -name 'ckpt_*.dmtcp' -print
)
[[ ${#checkpoints[@]} -eq 1 ]]
sha256sum -c "$base_dir/checkpoint.sha256"

mkdir -p "$output_dir/checkpoint" "$output_dir/dmtcp-tmp"
mkfifo "$output_dir/input.fifo" "$output_dir/output.fifo"
tail -f /dev/null >"$output_dir/input.fifo" &
keeper_pid=$!
tee "$output_dir/runtime.log" <"$output_dir/output.fifo" >/dev/null &
reader_pid=$!
runtime_pid=
cleanup() {
  kill "$keeper_pid" "$reader_pid" 2>/dev/null || true
  if [[ -n $runtime_pid ]]; then kill "$runtime_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT

driver_sha=$(sha256sum "$driver" | awk '{print $1}')
nonce=$(printf '%s\n%s\n%s\n' "$output_dir" "$driver_sha" "$expected_marker" |
  sha256sum | awk '{print $1}')
ack="CANDLE_RESTORE_INPUT_ACK nonce=$nonce"
{
  printf 'print_endline "%s";;\n' "$ack"
  printf '#use "%s";;\n' "$driver"
} >"$output_dir/input.fifo" &
writer_pid=$!

cd "$dev_runtime"
env -i PATH=/project/bin:/usr/local/bin:/usr/bin:/bin LC_ALL=C \
  CML_HEAP_SIZE=32768 DMTCP_TMPDIR="$output_dir/dmtcp-tmp" \
  timeout 21600 dmtcp_restart --new-coordinator --coord-port 0 \
    --port-file "$output_dir/coord.port" --ckptdir "$output_dir/checkpoint" \
    "${checkpoints[0]}" <"$output_dir/input.fifo" \
    >"$output_dir/output.fifo" 2>&1 &
runtime_pid=$!
printf '%s\n' "$runtime_pid" >"$output_dir/runtime.pid"
wait "$writer_pid"

fail() {
  reason=$1
  printf '%s\n' "$reason" | tee "$output_dir/CHECKPOINT-FAILED" >&2
  if [[ -s $output_dir/coord.port ]]; then
    dmtcp_command --port "$(<"$output_dir/coord.port")" -k \
      >>"$output_dir/dmtcp-checkpoint.log" 2>&1 || true
  fi
  exit 1
}

while true; do
  if rg -a -q 'ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory' \
       "$output_dir/runtime.log"; then
    fail 'restored runtime reported an error before the requested boundary'
  fi
  ack_count=$(rg -a -Fxc "$ack" "$output_dir/runtime.log" || true)
  marker_count=$(rg -a -Foc "$expected_marker" "$output_dir/runtime.log" || true)
  [[ $ack_count -le 1 ]] || fail 'restored input acknowledgement occurred more than once'
  [[ $marker_count -le 1 ]] || fail 'requested phase marker occurred more than once'
  if [[ $marker_count -eq 1 ]]; then
    [[ $ack_count -eq 1 ]] || fail 'phase completed without fresh-input acknowledgement'
    port=$(<"$output_dir/coord.port")
    dmtcp_command --port "$port" -bc >"$output_dir/dmtcp-checkpoint.log" 2>&1
    checkpoint=
    stable_size=
    stable_samples=0
    for _ in $(seq 1 1800); do
      mapfile -t fresh < <(
        find "$output_dir/checkpoint" -maxdepth 1 -type f -name 'ckpt_*.dmtcp' -print
      )
      mapfile -t temporary < <(
        find "$output_dir/checkpoint" -maxdepth 1 -name '*.temp' -print
      )
      if [[ ${#fresh[@]} -eq 1 && ${#temporary[@]} -eq 0 ]]; then
        current_size=$(stat -c '%s' "${fresh[0]}")
        if [[ $current_size -gt 0 && $current_size == "$stable_size" ]]; then
          stable_samples=$((stable_samples + 1))
        else
          stable_size=$current_size
          stable_samples=0
        fi
        if [[ $stable_samples -ge 2 ]]; then
          checkpoint=${fresh[0]}
          break
        fi
      elif [[ ${#fresh[@]} -gt 1 ]]; then
        fail 'more than one phase checkpoint was produced'
      fi
      sleep 1
    done
    [[ -n $checkpoint ]] || fail 'phase checkpoint did not finalize'
    sha256sum "$checkpoint" >"$output_dir/checkpoint.sha256"
    sha256sum "$output_dir/runtime.log" >"$output_dir/runtime-log.sha256"
    sha256sum "$driver" "$dev_runtime/cake" \
      "$dev_runtime/DEVELOPMENT-NONPROMOTABLE.json" \
      "$base_dir/checkpoint.receipt" >"$output_dir/input-files.sha256"
    printf '%s\n' \
      "receipt_kind=$receipt_kind" \
      'release_evidence=false' \
      'cml_heap_size_mib=32768' \
      "base_checkpoint=$(realpath "${checkpoints[0]}")" \
      "driver=$driver" \
      "driver_sha256=$driver_sha" \
      "expected_marker=$expected_marker" \
      "checkpoint=$checkpoint" \
      "checkpoint_size_bytes=$(stat -c '%s' "$checkpoint")" \
      "checkpoint_sha256=$(sha256sum "$checkpoint" | awk '{print $1}')" \
      "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      >"$output_dir/checkpoint.receipt"
    touch "$output_dir/CHECKPOINT-READY"
    dmtcp_command --port "$port" -k >>"$output_dir/dmtcp-checkpoint.log" 2>&1 || true
    set +e
    wait "$runtime_pid"
    set -e
    runtime_pid=
    wait "$reader_pid"
    reader_pid=
    kill "$keeper_pid" 2>/dev/null || true
    keeper_pid=
    exit 0
  fi
  kill -0 "$runtime_pid" 2>/dev/null ||
    fail 'restored runtime exited before the requested boundary'
  sleep 2
done
