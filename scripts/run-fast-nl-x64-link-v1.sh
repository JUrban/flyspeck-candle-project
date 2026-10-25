#!/usr/bin/env bash
set -euo pipefail

run=/project/flyspeck-candle-runs/v658-fast-nl-compiler64-final-stage-dev-001
cake=/project/worktrees/cakeml-direct-fast-nl-integration-v1
candle=/project/worktrees/candle-direct-fast-nl-runtime-v1
hol=/project/worktrees/HOL-cakeml-dopen-v13
project=/project/worktrees/flyspeck-project-candle-repin-prep-v13
trans=$cake/compiler/bootstrap/translation
x64=$cake/compiler/bootstrap/compilation/x64/64
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-aa7ffbc-0f9690d-bc47e65-attempt-001

cake_head=aa7ffbc3a5e30c0f78acfe883f39476d0a3f035a
candle_head=0f9690d3683efca78a60d4607596815245e37578
hol_head=bc47e6586a87ac538a71b10206a83c169c171d1a
project_head=e325a3ef6b0cd4e88bcdbf432de170d967364fa3

prefix=x64-link-v1
controller_status=$run/$prefix-controller.status
controller_receipt=$run/$prefix-controller.receipt
compiler_receipt=$run/compiler64-final-stage-v1.receipt
phase=preflight
status=1

finish() {
  printf '%s\n' "$status" >"$controller_status"
  {
    printf 'receipt_kind=development-fast-nl-x64-link-v1\n'
    printf 'release_evidence=false\n'
    printf 'status=%s\n' "$status"
    printf 'last_phase=%s\n' "$phase"
    printf 'cake_head=%s\n' "$cake_head"
    printf 'candle_head=%s\n' "$candle_head"
    printf 'hol_head=%s\n' "$hol_head"
    printf 'runtime=%s\n' "$runtime"
    printf 'finished_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"$controller_receipt"
  trap - EXIT
  exit "$status"
}
trap finish EXIT

[[ ! -e $controller_status ]]
[[ ! -e $controller_receipt ]]
[[ $(git -C "$cake" rev-parse HEAD) == "$cake_head" ]]
[[ $(git -C "$candle" rev-parse HEAD) == "$candle_head" ]]
[[ $(git -C "$hol" rev-parse HEAD) == "$hol_head" ]]
[[ $(git -C "$project" rev-parse HEAD) == "$project_head" ]]
[[ -z $(git -C "$cake" status --short) ]]
[[ -z $(git -C "$candle" status --short) ]]
[[ -z $(git -C "$hol" status --short) ]]
[[ -z $(git -C "$project" status --short) ]]
grep -Fxq 'status=0' "$compiler_receipt"
compiler_dat=$trans/.hol/objs/compiler64ProgTheory.dat
compiler_sml=$trans/.hol/objs/compiler64ProgTheory.sml
[[ -s $compiler_dat ]]
[[ -s $compiler_sml ]]
[[ $(sha256sum "$compiler_dat" | awk '{print $1}') == \
   $(sed -n 's/^theory_dat_sha256=//p' "$compiler_receipt") ]]
[[ $(sed -n 's/.*hash = "\([0-9a-f]*\)".*/\1/p' "$compiler_sml" | head -1) == \
   $(sed -n 's/^theory_hash=//p' "$compiler_receipt") ]]
[[ ! -e $runtime ]]

phase=x64-assembly
if [[ -e $x64/cake.S ]]; then
  sha256sum "$x64/cake.S" >"$run/$prefix-x64-before.sha256"
fi
set +e
(
  cd "$x64"
  /usr/bin/time -v "$hol/bin/Holmake" --heap-size=150000 \
    --no_prereqs -j1 cake.S
) >"$run/$prefix-x64.log" 2>&1
x64_status=$?
set -e
printf '%s\n' "$x64_status" >"$run/$prefix-x64.status"
[[ $x64_status -eq 0 ]]
[[ -s $x64/cake.S ]]
[[ $x64/cake.S -nt $compiler_dat ]]
sha256sum "$x64/cake.S" >"$run/$prefix-x64.sha256"

phase=development-link
set +e
/usr/bin/time -v -o "$run/$prefix-development-link.time" \
  python3 "$project/scripts/build-nonpromotable-candle-development.py" \
    --cakeml-root "$cake" \
    --cakeml-commit "$cake_head" \
    --candle-root "$candle" \
    --candle-commit "$candle_head" \
    --hol4-root "$hol" \
    --hol4-commit "$hol_head" \
    --output-root "$runtime" \
    >"$run/$prefix-development-link.log" 2>&1
link_status=$?
set -e
printf '%s\n' "$link_status" >"$run/$prefix-development-link.status"
[[ $link_status -eq 0 ]]
[[ -x $runtime/cake ]]

status=0
phase=complete
