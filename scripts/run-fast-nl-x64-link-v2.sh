#!/usr/bin/env bash
set -euo pipefail

run=/project/flyspeck-candle-runs/v662-fast-nl-x64-cv-rep-dev-001
failed_run=/project/flyspeck-candle-runs/v658-fast-nl-compiler64-final-stage-dev-001
cake=/project/worktrees/cakeml-direct-fast-nl-integration-v1
candle=/project/worktrees/candle-direct-fast-nl-runtime-v1
hol=/project/worktrees/HOL-cakeml-dopen-v13
project=/project/worktrees/flyspeck-project-candle-repin-prep-v13
trans=$cake/compiler/bootstrap/translation
x64=$cake/compiler/bootstrap/compilation/x64/64
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005

cake_head=b3fb54e9f822fd462b929843e816d1fa1dd46cfd
compiler_source_head=aa7ffbc3a5e30c0f78acfe883f39476d0a3f035a
candle_head=0f9690d3683efca78a60d4607596815245e37578
hol_head=bc47e6586a87ac538a71b10206a83c169c171d1a
project_head=e325a3ef6b0cd4e88bcdbf432de170d967364fa3

prefix=x64-link-v2
controller_status=$run/$prefix-controller.status
controller_receipt=$run/$prefix-controller.receipt
failed_receipt=$failed_run/compiler64-final-stage-v1.receipt
failed_log=$failed_run/compiler64-final-stage-v1.log
phase=preflight
status=1

finish() {
  printf '%s\n' "$status" >"$controller_status"
  {
    printf 'receipt_kind=development-fast-nl-x64-link-v2\n'
    printf 'release_evidence=false\n'
    printf 'status=%s\n' "$status"
    printf 'last_phase=%s\n' "$phase"
    printf 'cake_head=%s\n' "$cake_head"
    printf 'compiler_source_head=%s\n' "$compiler_source_head"
    printf 'candle_head=%s\n' "$candle_head"
    printf 'hol_head=%s\n' "$hol_head"
    printf 'compiler_theory_hash=82ee3e5ce08af05ea34610a6d75c9bea324962e6\n'
    printf 'compiler_theory_dat_sha256=acf5434b9839c1c8640d4f13fd0a457e83b41f56eeacbc809589846f27f84f9f\n'
    printf 'runtime=%s\n' "$runtime"
    printf 'finished_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"$controller_receipt"
  trap - EXIT
  exit "$status"
}
trap finish EXIT

mkdir -p "$run"
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
[[ $(git -C "$cake" diff --name-only "$compiler_source_head"..HEAD) == \
   compiler/bootstrap/compilation/x64/64/x64BootstrapScript.sml ]]

# Preserve the failed global-graph result.  It is not reclassified as a
# successful run: the following checks authenticate the completed target
# artifact separately before it is consumed by the x64 target.
grep -Fxq 'status=1' "$failed_receipt"
[[ $(<"$failed_run/compiler64-final-stage-v1.status") == 1 ]]
[[ $(sha256sum "$failed_log" | awk '{print $1}') == \
   e7884c834ffb55394f95c9536931ddc0a317b902ce077473c3bc8e8fdb601611 ]]
grep -Fxq 'Exporting theory "compiler64Prog" ... done.' "$failed_log"
grep -Fxq 'Theory "compiler64Prog" took 2h19m45s to build' "$failed_log"
grep -Fxq 'Holmake: [27/27] compiler64Prog' "$failed_log"

check_sha() {
  expected=$1
  path=$2
  [[ $(sha256sum "$path" | awk '{print $1}') == "$expected" ]]
}

compiler_dat=$trans/.hol/objs/compiler64ProgTheory.dat
compiler_sml=$trans/.hol/objs/compiler64ProgTheory.sml
check_sha acf5434b9839c1c8640d4f13fd0a457e83b41f56eeacbc809589846f27f84f9f \
  "$compiler_dat"
check_sha 2297da752160a2fb8f2b69f071c0d2408286e63aa6af1296a3283d0678a75fa0 \
  "$compiler_sml"
check_sha 6a545777f25a36682accf4ee4631150c9a165d6a95b2f9ddfdea912b98338362 \
  "$trans/.hol/objs/compiler64ProgTheory.sig"
check_sha a0c48cccbd07a854b04b085f4567daaf25eefd2a1686fd698ef17d7c7a52d025 \
  "$trans/.hol/objs/compiler64ProgTheory.ui"
check_sha 315ed3efb12a59b2600dbe258d897cbaa825b3b693e498050c4ad31a6fa469cf \
  "$trans/.hol/objs/compiler64ProgTheory.uo"
[[ $(stat -c '%s' "$compiler_dat") == 252987640 ]]
[[ $(sed -n 's/.*hash = "\([0-9a-f]*\)".*/\1/p' "$compiler_sml" | head -1) == \
   82ee3e5ce08af05ea34610a6d75c9bea324962e6 ]]
for theorem in \
  semantics_compiler64_prog_parser_capability \
  semantics_compiler64_prog_parser_ok \
  semantics_compiler64_prog_parser_error \
  semantics_compiler64_prog_parser_ok_exact \
  semantics_compiler64_prog_parser_error_exact \
  semantics_compiler64_prog \
  Decls_FRONT_compiler64_prog \
  LAST_compiler64_prog; do
  rg -q "\"$theorem\"" "$compiler_sml"
done

# The project-wide Holmake graph has an unrelated failed basis/basis-heap
# node.  Check the exact target in its own directory so that only that global
# aggregation is excluded; the x64 theory will load and consume this artifact
# immediately below.
phase=compiler-target-authentication
set +e
(
  cd "$trans"
  /usr/bin/time -v "$hol/bin/Holmake" --no-project --no_preexecs \
    --heap-size=150000 --no_prereqs -q -j1 compiler64ProgTheory.uo
) >"$run/$prefix-compiler-target-authentication.log" 2>&1
target_status=$?
set -e
printf '%s\n' "$target_status" >"$run/$prefix-compiler-target-authentication.status"
[[ $target_status -eq 0 ]]

phase=x64-assembly
if [[ -e $x64/cake.S ]]; then
  sha256sum "$x64/cake.S" >"$run/$prefix-x64-before.sha256"
fi
set +e
(
  cd "$x64"
  /usr/bin/time -v timeout 21600 "$hol/bin/Holmake" --no-project \
    --no_preexecs --rebuild_deps -I "$trans" --heap-size=150000 \
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
  timeout 7200 python3 "$project/scripts/build-nonpromotable-candle-development.py" \
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
