#!/usr/bin/env bash
set -euo pipefail

scripts=/project/flyspeck-candle-project/scripts
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-fixed-algebraic-item-invariant-v677m
output=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/algebraic-program-sound-diagnostic-v677p
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=/project/flyspeck-candle-project/tools/fast_nl_v677_algebraic_program_sound_diagnostic.ml

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
[[ -x $runtime/cake ]]

"$scripts/audit-fast-nl-v677-algebraic-program-sound-diagnostic.py" |
  tee /tmp/fast-nl-v677-algebraic-program-sound-diagnostic-audit.txt
grep -Fxq 'status=0' /tmp/fast-nl-v677-algebraic-program-sound-diagnostic-audit.txt

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_PHASE_TIMEOUT_SECONDS=900
export FAST_NL_PHASE_DRIVER_MODE=direct

"$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$base" "$output" "$driver" \
  CANDLE_FLYSPECK_V677_DIAGNOSTIC_UNEXPECTED_SUCCESS \
  development-fast-nl-v677-algebraic-program-sound-diagnostic-v1
