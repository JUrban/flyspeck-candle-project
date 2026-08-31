#!/bin/bash -p
# From a pristine CakeML worktree, build the base heap and run the exact
# four-stage CakeML x64 bootstrap proof replay serially.

set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "usage: $0 RUN_ROOT CAKEML_ROOT CAKEML_HEAD HOL4_ROOT HOL4_HEAD" >&2
  exit 64
fi

run_root=$1
cakeml_root=$2
cakeml_head=$3
hol4_root=$4
hol4_head=$5

if [[ $run_root != /* || $cakeml_root != /* || $hol4_root != /* ]]; then
  echo "run, CakeML, and HOL4 roots must be absolute" >&2
  exit 64
fi
if [[ $cakeml_root == / || $hol4_root == / ]]; then
  echo "refusing a filesystem root as a source root" >&2
  exit 64
fi

git_hardened() {
  /usr/bin/env -i \
    PATH=/usr/bin:/bin LC_ALL=C \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    GIT_TERMINAL_PROMPT=0 GIT_NO_REPLACE_OBJECTS=1 \
    /usr/bin/git \
      -c core.fsmonitor=false \
      -c core.untrackedCache=false \
      -c core.preloadIndex=false \
      "$@"
}

controller_invocation=$0
controller_script=$(/usr/bin/realpath -e "$controller_invocation")
controller_root=$(git_hardened -C "$(/usr/bin/dirname "$controller_script")" \
  rev-parse --show-toplevel)
controller_relative=scripts/run-canonical-bootstrap-replay.sh
gate_relative=scripts/check-canonical-bootstrap-gate.py
controller_head=$(git_hardened -C "$controller_root" rev-parse HEAD)
gate_script=$controller_root/$gate_relative

if [[ $controller_root != /* ]] ||
   [[ $controller_invocation != "$controller_script" ]] ||
   [[ $controller_root != "$(/usr/bin/realpath -e "$controller_root")" ]] ||
   [[ $controller_script != "$controller_root/$controller_relative" ]] ||
   [[ $gate_script != "$(/usr/bin/realpath -e "$gate_script")" ]] ||
   ! git_hardened -C "$controller_root" \
      ls-files --error-unmatch "$controller_relative" >/dev/null 2>&1 ||
   ! git_hardened -C "$controller_root" \
      ls-files --error-unmatch "$gate_relative" >/dev/null 2>&1 ||
   ! git_hardened -C "$controller_root" \
      show "$controller_head:$controller_relative" |
      /usr/bin/cmp -s - "$controller_script" ||
   ! git_hardened -C "$controller_root" \
      show "$controller_head:$gate_relative" |
      /usr/bin/cmp -s - "$gate_script"; then
  echo "replay controller or gate is outside committed project authority" >&2
  exit 65
fi

# Keep the exact committed controller source open read-only across both
# publisher execs.  The gate authenticates this descriptor together with the
# parent's exact /proc command line and executable identity.
exec 9<"$controller_script"

if [[ $cakeml_root != "$(/usr/bin/realpath -e "$cakeml_root")" ]] ||
   [[ $hol4_root != "$(/usr/bin/realpath -e "$hol4_root")" ]]; then
  echo "CakeML and HOL4 roots must be exact canonical directories" >&2
  exit 64
fi

run_parent=$(/usr/bin/dirname "$run_root")
run_name=$(/usr/bin/basename "$run_root")
if [[ $run_name == . || $run_name == .. ]] ||
   [[ $run_parent != "$(/usr/bin/realpath -e "$run_parent")" ]] ||
   [[ $run_root != "$run_parent/$run_name" ]]; then
  echo "run root must be a new direct child of an exact canonical directory" >&2
  exit 64
fi
if [[ -e $run_root || -L $run_root ]]; then
  echo "run root already exists: $run_root" >&2
  exit 65
fi

gate_command=(/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$gate_script")
exact_git() {
  "${gate_command[@]}" --internal-exact-git \
    --root "$1" --head "$2" --label "$3" "${@:4}" >/dev/null
}

# This first exact check is intentionally before run-root creation.  In
# particular, a stale ignored base heap or .hol cache leaves no receipt root.
exact_git "$controller_root" "$controller_head" "replay controller project"
exact_git "$cakeml_root" "$cakeml_head" CakeML --require-no-ignored
exact_git "$hol4_root" "$hol4_head" HOL4

if /usr/bin/pgrep -x Holmake >/dev/null; then
  echo "another Holmake process is live" >&2
  exit 65
fi

umask 077
/usr/bin/mkdir "$run_root"
if [[ $run_root != "$(/usr/bin/realpath -e "$run_root")" ]]; then
  echo "created run root is not exact" >&2
  exit 65
fi

controller_pgid=$(/usr/bin/ps -o pgid= -p "$$")
controller_pgid=${controller_pgid//[[:space:]]/}
if [[ ! $controller_pgid =~ ^[0-9]+$ ]] || (( controller_pgid <= 1 )); then
  echo "could not identify controller process group" >&2
  exit 65
fi

/usr/bin/printf '%s\n' "$cakeml_root" >"$run_root/cakeml_root"
/usr/bin/printf '%s\n' "$cakeml_head" >"$run_root/cakeml_head"
/usr/bin/printf '%s\n' "$hol4_root" >"$run_root/hol4_root"
/usr/bin/printf '%s\n' "$hol4_head" >"$run_root/hol4_head"
/usr/bin/printf '%s\n' "$controller_root" >"$run_root/controller_project_root"
/usr/bin/printf '%s\n' "$controller_head" >"$run_root/controller_project_head"
/usr/bin/printf '%s\n' "$controller_relative" \
  >"$run_root/controller_script_relative"
/usr/bin/printf '%s\n' "$gate_relative" >"$run_root/gate_script_relative"
/usr/bin/sha256sum "$controller_script" | /usr/bin/awk '{print $1}' \
  >"$run_root/controller_script_sha256"
/usr/bin/sha256sum "$gate_script" | /usr/bin/awk '{print $1}' \
  >"$run_root/gate_script_sha256"
/usr/bin/printf '%s\n' none >"$run_root/cakeml_ignored_products_preflight"
/usr/bin/printf '%s\n' "$$" >"$run_root/controller_pid"
/usr/bin/printf '%s\n' "$controller_pgid" >"$run_root/controller_pgid"
/usr/bin/printf '%s\n' "-j1 --mt=1" >"$run_root/build_parallelism"
/usr/bin/printf '%s\n' "117964800" >"$run_root/address_space_limit_kib"
/usr/bin/date -u +%FT%TZ >"$run_root/started_utc"

# Revalidate all three tracked trees and publish the authenticated historical
# empty-product observation immediately before any build command.
"${gate_command[@]}" --internal-write-preflight \
  --replay-root "$run_root" \
  --controller-pid "$$" --controller-pgid "$controller_pgid" \
  --project-root "$controller_root" --project-head "$controller_head" \
  --cakeml-root "$cakeml_root" --cakeml-head "$cakeml_head" \
  --hol4-root "$hol4_root" --hol4-head "$hol4_head" >/dev/null

# 115.2 GiB in KiB. The user-authorized exceptional ceiling is 120 GiB.
ulimit -v 117964800

run_stage() {
  local stage=$1
  local directory=$2
  local target=$3
  local receipt=$4
  local log=$5
  /usr/bin/printf '%s\n' "$stage" >"$run_root/stage"
  (
    exec 9<&-
    cd "$directory"
    /usr/bin/time -v -o "$run_root/$receipt" \
      "$hol4_root/bin/Holmake" -j1 --mt=1 "$target" \
      >"$run_root/$log" 2>&1
  )
}

run_stage cakeml-heap \
  "$cakeml_root/misc" cakeml-heap \
  00-cakeml-heap.time 00-cakeml-heap.log
run_stage cake_compile_heap \
  "$cakeml_root/cv_translator" cake_compile_heap \
  01-cake-compile-heap.time 01-cake-compile-heap.log
run_stage compiler64ProgTheory.uo \
  "$cakeml_root/compiler/bootstrap/translation" compiler64ProgTheory.uo \
  02-compiler64Prog.time 02-compiler64Prog.log
run_stage x64BootstrapTheory.uo \
  "$cakeml_root/compiler/bootstrap/compilation/x64/64" x64BootstrapTheory.uo \
  03-x64Bootstrap.time 03-x64Bootstrap.log
run_stage x64BootstrapProofTheory.uo \
  "$cakeml_root/compiler/bootstrap/compilation/x64/64/proofs" \
  x64BootstrapProofTheory.uo \
  04-x64BootstrapProof.time 04-x64BootstrapProof.log

/usr/bin/date -u +%FT%TZ >"$run_root/finished_utc"
"${gate_command[@]}" --internal-publish-manifest \
  --replay-root "$run_root" \
  --controller-pid "$$" --controller-pgid "$controller_pgid" \
  --project-root "$controller_root" --project-head "$controller_head" \
  --cakeml-root "$cakeml_root" --cakeml-head "$cakeml_head" \
  --hol4-root "$hol4_root" --hol4-head "$hol4_head"
/usr/bin/printf '%s\n' complete >"$run_root/stage"
