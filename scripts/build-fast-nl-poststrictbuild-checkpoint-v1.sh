#!/usr/bin/env bash
set -euo pipefail

run_dir=/project/flyspeck-candle-runs/v658-fast-nl-compiler64-final-stage-dev-001
fixture_dir=/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001
dev_runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-aa7ffbc-0f9690d-bc47e65-attempt-001
base_source=/project/worktrees/flyspeck-strictbuild-checkpoint-base-9ae969df
ready_marker=CANDLE_FLYSPECK_V656_FAST_NL_POSTSTRICTBUILD_CHECKPOINT_READY
setup=$fixture_dir/setup.ml

[[ ! -e $run_dir/base.log ]]
[[ -z $(git -C "$base_source" status --short) ]]
[[ $(git -C "$base_source" rev-parse HEAD) == \
   9ae969dfaca95e223d44b50f7cae00df3d2ab949 ]]
[[ -x $dev_runtime/cake ]]
grep -Fxq 'status=0' "$run_dir/x64-link-v1-controller.receipt"
jq -e '
  .repositories.cakeml.commit == "aa7ffbc3a5e30c0f78acfe883f39476d0a3f035a" and
  .repositories.candle.commit == "0f9690d3683efca78a60d4607596815245e37578" and
  .repositories.hol4.commit == "bc47e6586a87ac538a71b10206a83c169c171d1a"
' "$dev_runtime/DEVELOPMENT-NONPROMOTABLE.json" >/dev/null
[[ $(sha256sum "$setup" | awk '{print $1}') == \
   f287fc3bfff250d57d5804ba43bcf1287a383e9b029015e905815b770ac1942b ]]

mkdir -p "$run_dir/checkpoint" "$run_dir/dmtcp-tmp"
mkfifo "$run_dir/input.fifo" "$run_dir/output.fifo"
tail -f /dev/null >"$run_dir/input.fifo" &
keeper_pid=$!
tee "$run_dir/base.log" <"$run_dir/output.fifo" >/dev/null &
reader_pid=$!
runtime_pid=
cleanup() {
  kill "$keeper_pid" "$reader_pid" 2>/dev/null || true
  if [[ -n $runtime_pid ]]; then kill "$runtime_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT

cd "$dev_runtime"
env -i PATH=/project/bin:/usr/local/bin:/usr/bin:/bin LC_ALL=C \
  CML_HEAP_SIZE=32768 DMTCP_TMPDIR="$run_dir/dmtcp-tmp" \
  timeout 21600 dmtcp_launch --new-coordinator --coord-port 0 \
    --port-file "$run_dir/coord.port" --ckptdir "$run_dir/checkpoint" \
    "$dev_runtime/cake" --candle \
    <"$run_dir/input.fifo" >"$run_dir/output.fifo" 2>&1 &
runtime_pid=$!
printf '%s\n' "$runtime_pid" >"$run_dir/runtime.pid"

for _ in $(seq 1 300); do
  [[ -s $run_dir/coord.port ]] && break
  kill -0 "$runtime_pid" 2>/dev/null || break
  sleep 0.1
done
[[ -s $run_dir/coord.port ]]
sed -n '1,$p' "$setup" >"$run_dir/input.fifo"

fail() {
  reason=$1
  printf '%s\n' "$reason" | tee "$run_dir/CHECKPOINT-FAILED" >&2
  if [[ -s $run_dir/coord.port ]]; then
    dmtcp_command --port "$(<"$run_dir/coord.port")" -k \
      >>"$run_dir/dmtcp-checkpoint.log" 2>&1 || true
  fi
  exit 1
}

while true; do
  if rg -a -q 'ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory' \
       "$run_dir/base.log"; then
    fail 'runtime reported a source error before post-strictbuild readiness'
  fi
  ready_count=$(rg -a -Foc "$ready_marker" "$run_dir/base.log" || true)
  [[ $ready_count -le 1 ]] || fail 'post-strictbuild marker occurred more than once'
  if [[ $ready_count -eq 1 ]]; then
    port=$(<"$run_dir/coord.port")
    dmtcp_command --port "$port" -bc >"$run_dir/dmtcp-checkpoint.log" 2>&1
    checkpoint=
    stable_size=
    stable_samples=0
    for _ in $(seq 1 1800); do
      mapfile -t checkpoints < <(
        find "$run_dir/checkpoint" -maxdepth 1 -type f -name 'ckpt_*.dmtcp' -print
      )
      mapfile -t temporary < <(
        find "$run_dir/checkpoint" -maxdepth 1 -name '*.temp' -print
      )
      if [[ ${#checkpoints[@]} -eq 1 && ${#temporary[@]} -eq 0 ]]; then
        current_size=$(stat -c '%s' "${checkpoints[0]}")
        if [[ $current_size -gt 0 && $current_size == "$stable_size" ]]; then
          stable_samples=$((stable_samples + 1))
        else
          stable_size=$current_size
          stable_samples=0
        fi
        if [[ $stable_samples -ge 2 ]]; then
          checkpoint=${checkpoints[0]}
          break
        fi
      elif [[ ${#checkpoints[@]} -gt 1 ]]; then
        fail 'more than one post-strictbuild checkpoint was produced'
      fi
      sleep 1
    done
    [[ -n $checkpoint ]] || fail 'post-strictbuild checkpoint did not finalize'
    sha256sum "$checkpoint" >"$run_dir/checkpoint.sha256"
    sha256sum "$run_dir/base.log" >"$run_dir/base-log.sha256"
    sha256sum "$dev_runtime/cake" \
      "$dev_runtime/DEVELOPMENT-NONPROMOTABLE.json" "$setup" \
      "$fixture_dir/extra-source-identities.ml" \
      "$fixture_dir/fast-nl-source-aliases.ml" \
      "$fixture_dir/flyspeck_stratum_fast_nl_setup.ml" \
      >"$run_dir/input-files.sha256"
    printf '%s\n' \
      'receipt_kind=development-fast-nl-post-strictbuild-checkpoint-v1' \
      'release_evidence=false' \
      'direct_actions_reached=0' \
      'direct_actions_passed=0' \
      'authenticated_fast_nl_source_count=207' \
      'authenticated_byte_equal_source_alias_count=28' \
      'cml_heap_size_mib=32768' \
      'cakeml_commit=aa7ffbc3a5e30c0f78acfe883f39476d0a3f035a' \
      'candle_commit=0f9690d3683efca78a60d4607596815245e37578' \
      'hol4_commit=bc47e6586a87ac538a71b10206a83c169c171d1a' \
      "checkpoint=$checkpoint" \
      "checkpoint_size_bytes=$(stat -c '%s' "$checkpoint")" \
      "checkpoint_sha256=$(sha256sum "$checkpoint" | awk '{print $1}')" \
      "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      >"$run_dir/checkpoint.receipt"
    touch "$run_dir/CHECKPOINT-READY"
    dmtcp_command --port "$port" -k >>"$run_dir/dmtcp-checkpoint.log" 2>&1 || true
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
    fail 'runtime exited before post-strictbuild readiness'
  sleep 2
done
