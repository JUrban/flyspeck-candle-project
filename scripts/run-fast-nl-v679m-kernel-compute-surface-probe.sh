#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-tag10-flat-input-v679l
output=/project/flyspeck-candle-runs/v679m-fast-nl-kernel-compute-surface-probe-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=$project/tools/fast_nl_v679m_kernel_compute_surface_probe.ml
predecessor_audit=$project/scripts/audit-fast-nl-v679l-import-prepared-input-flat.py
marker='CANDLE_FLYSPECK_V679M_KERNEL_COMPUTE_SURFACE_OK DEVELOPMENT_NON_RELEASE result=1 assumptions=0'

[[ ! -e $output ]]
[[ -f $driver && ! -L $driver ]]
[[ -x $predecessor_audit ]]
preflight=$($predecessor_audit)
[[ $(grep -Fxc 'status=0' <<<"$preflight") -eq 2 ]]
grep -Fxq \
  'checkpoint_sha256=07c921204ebe48ad01ffce1c8484785af27b767f4df74500fff058eedfb3946d' \
  <<<"$preflight"

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=600

"$project/scripts/run-fast-nl-restored-input-probe-v1.sh" \
  "$base" "$output" "$driver" "$marker"
