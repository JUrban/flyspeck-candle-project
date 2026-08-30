#!/usr/bin/env bash
# Run the exact four-stage CakeML x64 bootstrap proof replay serially.

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
if [[ -e $run_root ]]; then
  echo "run root already exists: $run_root" >&2
  exit 65
fi
if [[ $cakeml_root == / || $hol4_root == / ]]; then
  echo "refusing a filesystem root as a source root" >&2
  exit 64
fi

git_clean_at_head() {
  local root=$1
  local expected=$2
  local label=$3
  local observed
  observed=$(/usr/bin/git -C "$root" rev-parse HEAD)
  if [[ $observed != "$expected" ]]; then
    echo "$label head mismatch: $observed" >&2
    exit 65
  fi
  if [[ -n $(/usr/bin/git -C "$root" status --porcelain=v1 --untracked-files=all) ]]; then
    echo "$label worktree is not clean" >&2
    exit 65
  fi
}

git_clean_at_head "$cakeml_root" "$cakeml_head" CakeML
git_clean_at_head "$hol4_root" "$hol4_head" HOL4

if /usr/bin/pgrep -x Holmake >/dev/null; then
  echo "another Holmake process is live" >&2
  exit 65
fi

umask 077
/usr/bin/mkdir "$run_root"
/usr/bin/printf '%s\n' "$cakeml_head" >"$run_root/cakeml_head"
/usr/bin/printf '%s\n' "$hol4_head" >"$run_root/hol4_head"
/usr/bin/printf '%s\n' "$$" >"$run_root/controller_pid"
/usr/bin/printf '%s\n' "-j1 --mt=1" >"$run_root/build_parallelism"
/usr/bin/printf '%s\n' "117964800" >"$run_root/address_space_limit_kib"
/usr/bin/date -u +%FT%TZ >"$run_root/started_utc"

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
    cd "$directory"
    /usr/bin/time -v -o "$run_root/$receipt" \
      "$hol4_root/bin/Holmake" -j1 --mt=1 "$target" \
      >"$run_root/$log" 2>&1
  )
}

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

/usr/bin/printf '%s\n' complete >"$run_root/stage"
/usr/bin/date -u +%FT%TZ >"$run_root/finished_utc"
