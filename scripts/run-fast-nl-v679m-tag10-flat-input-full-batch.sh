#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-tag10-flat-input-v679l
output=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-tag10-flat-full-batch-v679m
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=$project/tools/fast_nl_v679m_tag10_flat_input_full_batch.ml
audit=$project/scripts/audit-fast-nl-v679m-tag10-flat-input-full-batch.py
marker='CANDLE_FLYSPECK_V679M_TAG10_FLAT_INPUT_FULL_BATCH_READY DEVELOPMENT_NON_RELEASE cells=4173 result=1 authenticated_aux_roots=16692 assumptions=0 axiom_growth=0'

[[ ! -e $output ]]
preflight=$($audit --preflight)
grep -Fxq 'status=0' <<<"$preflight"
grep -Fxq 'cells=4173' <<<"$preflight"
grep -Fxq 'numerical_compute_count=1' <<<"$preflight"

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_PHASE_TIMEOUT_SECONDS=1200
export FAST_NL_PHASE_DRIVER_MODE=source

"$project/scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$base" "$output" "$driver" "$marker" \
  development-fast-nl-v679m-tag10-flat-full-batch-checkpoint-v1

postflight=$($audit)
grep -Fxq 'status=0' <<<"$postflight"
grep -Fxq 'cells=4173' <<<"$postflight"
grep -Fxq 'result=1' <<<"$postflight"
