#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
scripts=$project/scripts
run=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
x64_receipt=/project/flyspeck-candle-runs/v662-fast-nl-x64-cv-rep-dev-001/x64-link-v2-controller.receipt
setup=$project/tools/fast_nl_v665_setup.ml
identity_extension=$project/tools/fast_nl_v665_verifier_data.ml
setup_sha256=6717554e10ada74a544472b72f5c51d27fc6209f3db6c2b41a7c93652a539b54
identity_extension_sha256=f31dc7f58d36207d8839f7cf72b084a82264ef8d910b8d6bc7eaac6e038356b5

[[ ! -e $run ]]
[[ $(sha256sum "$setup" | awk '{print $1}') == "$setup_sha256" ]]
[[ $(sha256sum "$identity_extension" | awk '{print $1}') == \
   "$identity_extension_sha256" ]]
grep -Fxq 'status=0' "$x64_receipt"

static_preflight=$(mktemp)
cleanup() {
  rm -f "$static_preflight"
}
trap cleanup EXIT
"$scripts/preflight-fast-nl-v665-support.sh" >"$static_preflight"
grep -Fxq 'status=0' "$static_preflight"

mkdir -p "$run"
cp "$static_preflight" "$run/static-preflight.receipt"

export FAST_NL_RUN_DIR=$run
export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_X64_RECEIPT=$x64_receipt
export FAST_NL_CAKE_HEAD=b3fb54e9f822fd462b929843e816d1fa1dd46cfd
export FAST_NL_SETUP=$setup
export FAST_NL_SETUP_SHA256=$setup_sha256
export FAST_NL_IDENTITY_EXTENSION=$identity_extension
export FAST_NL_IDENTITY_EXTENSION_SHA256=$identity_extension_sha256
export FAST_NL_AUTHENTICATED_SOURCE_COUNT=283
export FAST_NL_READY_MARKER=CANDLE_FLYSPECK_V665_FAST_NL_POSTSTRICTBUILD_CHECKPOINT_READY
export FAST_NL_BASE_TIMEOUT_SECONDS=3600

"$scripts/build-fast-nl-poststrictbuild-checkpoint-v1.sh"
