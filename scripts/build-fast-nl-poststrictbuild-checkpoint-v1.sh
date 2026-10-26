#!/usr/bin/env bash
set -euo pipefail

run_dir=${FAST_NL_RUN_DIR:-/project/flyspeck-candle-runs/v658-fast-nl-compiler64-final-stage-dev-001}
fixture_dir=/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001
dev_runtime=${FAST_NL_DEV_RUNTIME:-/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-aa7ffbc-0f9690d-bc47e65-attempt-001}
x64_receipt=${FAST_NL_X64_RECEIPT:-$run_dir/x64-link-v1-controller.receipt}
cake_head=${FAST_NL_CAKE_HEAD:-aa7ffbc3a5e30c0f78acfe883f39476d0a3f035a}
base_source=/project/worktrees/flyspeck-strictbuild-checkpoint-base-9ae969df
ready_marker=${FAST_NL_READY_MARKER:-CANDLE_FLYSPECK_V656_FAST_NL_POSTSTRICTBUILD_CHECKPOINT_READY}
setup=${FAST_NL_SETUP:-$fixture_dir/setup.ml}
setup_sha256=${FAST_NL_SETUP_SHA256:-f287fc3bfff250d57d5804ba43bcf1287a383e9b029015e905815b770ac1942b}
identity_extension=${FAST_NL_IDENTITY_EXTENSION:-}
identity_extension_sha256=${FAST_NL_IDENTITY_EXTENSION_SHA256:-}
authenticated_source_count=${FAST_NL_AUTHENTICATED_SOURCE_COUNT:-207}
base_timeout_seconds=${FAST_NL_BASE_TIMEOUT_SECONDS:-21600}

/project/flyspeck-candle-project/scripts/require-long-run-hazard-preflight.sh \
  "$base_timeout_seconds"

check_sha() {
  expected=$1
  path=$2
  [[ $(sha256sum "$path" | awk '{print $1}') == "$expected" ]]
}

[[ ! -e $run_dir/base.log ]]
[[ $authenticated_source_count =~ ^[0-9]+$ ]]
[[ $base_timeout_seconds =~ ^[1-9][0-9]*$ ]]
[[ -z $(git -C "$base_source" status --short) ]]
[[ $(git -C "$base_source" rev-parse HEAD) == \
   9ae969dfaca95e223d44b50f7cae00df3d2ab949 ]]
[[ -x $dev_runtime/cake ]]
grep -Fxq 'status=0' "$x64_receipt"
jq -e --arg cake_head "$cake_head" '
  .repositories.cakeml.commit == $cake_head and
  .repositories.candle.commit == "0f9690d3683efca78a60d4607596815245e37578" and
  .repositories.hol4.commit == "bc47e6586a87ac538a71b10206a83c169c171d1a"
' "$dev_runtime/DEVELOPMENT-NONPROMOTABLE.json" >/dev/null
check_sha "$setup_sha256" "$setup"
identity_extension_inputs=()
if [[ -n $identity_extension ]]; then
  [[ -n $identity_extension_sha256 ]]
  check_sha "$identity_extension_sha256" "$identity_extension"
  identity_extension_inputs+=("$identity_extension")
else
  [[ -z $identity_extension_sha256 ]]
fi
check_sha d850b246d4b8746362de3b019bc3ab4773a1de5f1da48dd48759c2dde2b270b9 \
  "$fixture_dir/extra-source-identities.ml"
check_sha b5eb3e0aa37a30b76ee503874df50390c756b0fb9049e9cd3e5b005cd214d40f \
  "$fixture_dir/fast-nl-source-aliases.ml"
check_sha 602f32b933c611bcb745adf596d46042fa51a474dfdb4a60ab974c8b3e2af7d0 \
  "$fixture_dir/flyspeck_stratum_fast_nl_setup.ml"
check_sha 0174c32fd75dd9db8027c9dddfef46cd6a98afd58c4f48345203800158ab03ce \
  "$fixture_dir/action0-through49.ml"
check_sha c1933e76dab724e7ea85199e306c4cf91d5f2a4dafbc246d0b469f17493c9d9b \
  "$fixture_dir/support.ml"
check_sha e2129e131a7ce4df7f1d5792f4799c98f111a6ecf54dfab181ba95a8455e8cd8 \
  "$fixture_dir/exact-one-call.ml"

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
  timeout "$base_timeout_seconds" dmtcp_launch --new-coordinator --coord-port 0 \
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
      "${identity_extension_inputs[@]}" \
      "$fixture_dir/extra-source-identities.ml" \
      "$fixture_dir/fast-nl-source-aliases.ml" \
      "$fixture_dir/flyspeck_stratum_fast_nl_setup.ml" \
      >"$run_dir/input-files.sha256"
    printf '%s\n' \
      'receipt_kind=development-fast-nl-post-strictbuild-checkpoint-v1' \
      'release_evidence=false' \
      'direct_actions_reached=0' \
      'direct_actions_passed=0' \
      "authenticated_fast_nl_source_count=$authenticated_source_count" \
      'authenticated_byte_equal_source_alias_count=28' \
      'cml_heap_size_mib=32768' \
      "cakeml_commit=$cake_head" \
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
