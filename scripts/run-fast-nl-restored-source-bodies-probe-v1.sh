#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  printf 'usage: %s BASE_DIR OUTPUT_DIR MARKER SOURCE...\n' "$0" >&2
  exit 2
fi

base=$1
output=$2
marker=$3
shift 3
sources=("$@")
runtime=${FAST_NL_DEV_RUNTIME:-/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005}
timeout_seconds=${FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS:-600}
checkpoint_after_success=${FAST_NL_SOURCE_BODIES_CHECKPOINT_AFTER_SUCCESS:-0}

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
[[ -x $runtime/cake ]]
[[ $timeout_seconds =~ ^[1-9][0-9]*$ ]]
[[ $checkpoint_after_success == 0 || $checkpoint_after_success == 1 ]]
for source in "${sources[@]}"; do
  if [[ $source != /* ]]; then
    printf 'source path must be absolute: %s\n' "$source" >&2
    exit 2
  fi
  [[ -f $source ]]
done
sha256sum -c "$base/checkpoint.sha256"
mapfile -t checkpoints < <(
  find "$base/checkpoint" -maxdepth 1 -type f -name 'ckpt_*.dmtcp' -print
)
[[ ${#checkpoints[@]} -eq 1 ]]

mkdir -p "$output/dmtcp-tmp"
if [[ $checkpoint_after_success == 1 ]]; then
  mkdir -p "$output/checkpoint"
fi
mkfifo "$output/input.fifo" "$output/output.fifo"
tail -f /dev/null >"$output/input.fifo" &
keeper_pid=$!
tee "$output/runtime.log" <"$output/output.fifo" >/dev/null &
reader_pid=$!
runtime_pid=
writer_pid=
cleanup() {
  kill "$keeper_pid" "$reader_pid" 2>/dev/null || true
  if [[ -n $writer_pid ]]; then kill "$writer_pid" 2>/dev/null || true; fi
  if [[ -n $runtime_pid ]]; then kill "$runtime_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT

checkpoint_sha=$(sha256sum "${checkpoints[0]}" | awk '{print $1}')
source_set_sha=$(
  sha256sum "${sources[@]}" | sha256sum | awk '{print $1}'
)
nonce=$(printf '%s\n%s\n%s\n' "$checkpoint_sha" "$source_set_sha" "$output" |
  sha256sum | awk '{print $1}')
ack="CANDLE_RESTORE_INPUT_ACK nonce=$nonce"
ready="CANDLE_RESTORE_REPL_READY nonce=$nonce"

started=$(date +%s)
started_ns=$(date +%s%N)
cd "$runtime"
restart_args=(
  --new-coordinator --coord-port 0 --port-file "$output/coord.port"
)
if [[ $checkpoint_after_success == 1 ]]; then
  restart_args+=(--ckptdir "$output/checkpoint")
fi
env -i PATH=/project/bin:/usr/local/bin:/usr/bin:/bin LC_ALL=C \
  CML_HEAP_SIZE=32768 DMTCP_TMPDIR="$output/dmtcp-tmp" \
  timeout "$timeout_seconds" dmtcp_restart "${restart_args[@]}" \
    "${checkpoints[0]}" \
    <"$output/input.fifo" >"$output/output.fifo" 2>&1 &
runtime_pid=$!
printf '%s\n' "$runtime_pid" >"$output/runtime.pid"

# DMTCP can open the inherited stdin FIFO before the restored Cake process is
# ready to consume it.  Sending the proof body at that point races restoration
# and can lose the entire input while leaving an apparently healthy idle REPL.
# Probe until the restored top level itself acknowledges a fresh phrase, then
# and only then send the authenticated source set.  Prefix the marker with a
# newline so it remains an exact log line even when the REPL has printed a
# prompt without a trailing newline.
ready_seen=0
for _ in $(seq 1 "$timeout_seconds"); do
  if [[ $(rg -a -Fxc "$ready" "$output/runtime.log" || true) -ge 1 ]]; then
    ready_seen=1
    break
  fi
  if ! kill -0 "$runtime_pid" 2>/dev/null; then
    printf '%s\n' 'restored source-bodies probe exited before REPL readiness' \
      >"$output/PROBE-FAILED"
    break
  fi
  printf 'print_endline ("\\n%s");;\n' "$ready" >"$output/input.fifo"
  sleep 1
done
if [[ $ready_seen -ne 1 ]]; then
  [[ -f $output/PROBE-FAILED ]] ||
    printf '%s\n' 'restored source-bodies probe timed out before REPL readiness' \
      >"$output/PROBE-FAILED"
  exit 1
fi
ready_ns=$(date +%s%N)
restore_to_ready_seconds=$(
  awk -v started="$started_ns" -v ready="$ready_ns" \
    'BEGIN {printf "%.6f", (ready - started) / 1000000000}'
)

{
  printf 'print_endline ("\\n%s");;\n' "$ack"
  for source in "${sources[@]}"; do
    # Prerequisites are already authenticated in the checkpoint.  These
    # development modules are streamed as fresh test input, so suppress only
    # their loader directives; do not mutate their definitions or proofs.
    sed '/^needs /d' "$source"
  done
} >"$output/input.fifo" &
writer_pid=$!
wait "$writer_pid"
writer_pid=

status=1
for _ in $(seq 1 "$timeout_seconds"); do
  if rg -a -q 'ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory' \
       "$output/runtime.log"; then
    printf '%s\n' 'restored source-bodies probe observed a Candle error' \
      >"$output/PROBE-FAILED"
    break
  fi
  ack_count=$(rg -a -Fxc "$ack" "$output/runtime.log" || true)
  marker_count=$(rg -a -Foc "$marker" "$output/runtime.log" || true)
  if [[ $ack_count -eq 1 && $marker_count -eq 1 ]]; then
    status=0
    break
  fi
  if ! kill -0 "$runtime_pid" 2>/dev/null; then
    printf '%s\n' 'restored source-bodies probe exited before fresh markers' \
      >"$output/PROBE-FAILED"
    break
  fi
  sleep 1
done

if [[ $status -ne 0 ]]; then
  [[ -f $output/PROBE-FAILED ]] ||
    printf '%s\n' 'restored source-bodies probe timed out before fresh markers' \
      >"$output/PROBE-FAILED"
  exit 1
fi

port=$(<"$output/coord.port")
fresh_checkpoint=
if [[ $checkpoint_after_success == 1 ]]; then
  dmtcp_command --port "$port" -bc >"$output/dmtcp-checkpoint.log" 2>&1
  stable_size=
  stable_samples=0
  for _ in $(seq 1 1800); do
    mapfile -t fresh < <(
      find "$output/checkpoint" -maxdepth 1 -type f -name 'ckpt_*.dmtcp' -print
    )
    mapfile -t temporary < <(
      find "$output/checkpoint" -maxdepth 1 -name '*.temp' -print
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
        fresh_checkpoint=${fresh[0]}
        break
      fi
    elif [[ ${#fresh[@]} -gt 1 ]]; then
      printf '%s\n' 'more than one source-bodies checkpoint was produced' \
        >"$output/PROBE-FAILED"
      exit 1
    fi
    sleep 1
  done
  if [[ -z $fresh_checkpoint ]]; then
    printf '%s\n' 'source-bodies checkpoint did not finalize' \
      >"$output/PROBE-FAILED"
    exit 1
  fi
  sha256sum "$fresh_checkpoint" >"$output/checkpoint.sha256"
fi
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
sha256sum "${sources[@]}" >"$output/source-bodies.sha256"
printf '%s\n' \
  'receipt_kind=development-fast-nl-restored-source-bodies-probe-v1' \
  'release_evidence=false' \
  "base_checkpoint=${checkpoints[0]}" \
  "base_checkpoint_sha256=$checkpoint_sha" \
  "source_set_sha256=$source_set_sha" \
  "fresh_ready=$ready" \
  "fresh_ack=$ack" \
  "expected_marker=$marker" \
  "restore_to_repl_ready_seconds=$restore_to_ready_seconds" \
  "elapsed_seconds=$elapsed" \
  "checkpoint_after_success=$checkpoint_after_success" \
  "runtime_exit_after_stop=$runtime_status" \
  "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >"$output/input-probe.receipt"
if [[ $checkpoint_after_success == 1 ]]; then
  printf '%s\n' \
    'receipt_kind=development-fast-nl-restored-source-bodies-checkpoint-v1' \
    'release_evidence=false' \
    "base_checkpoint=${checkpoints[0]}" \
    "base_checkpoint_sha256=$checkpoint_sha" \
    "source_set_sha256=$source_set_sha" \
    "expected_marker=$marker" \
    "checkpoint=$fresh_checkpoint" \
    "checkpoint_size_bytes=$(stat -c '%s' "$fresh_checkpoint")" \
    "checkpoint_sha256=$(sha256sum "$fresh_checkpoint" | awk '{print $1}')" \
    "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    >"$output/checkpoint.receipt"
  touch "$output/CHECKPOINT-READY"
fi
touch "$output/PROBE-PASSED"
