#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: $0 TRACE_BINARY RUN_DIRECTORY [RUNS]" >&2
  exit 2
fi

trace_binary=$1
run_directory=$2
runs=${3:-7}

[[ -x "$trace_binary" ]] || { echo "missing executable: $trace_binary" >&2; exit 2; }
[[ "$runs" =~ ^[1-9][0-9]*$ ]] || { echo "RUNS must be positive" >&2; exit 2; }

mkdir "$run_directory"

{
  echo "status=DEVELOPMENT_NON_RELEASE"
  echo "issued_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "runs=$runs"
  echo "authenticated_cells=875"
  echo "word64_full_products=34093928"
  echo "bounded128_additions=33004687"
  echo "bounded192_additions=1464750"
  echo "bounded128_floor40_shifts=11663750"
  echo "sign_dispatches=8168125"
  echo "rounding_predicate_dispatches=23327500"
  echo "bounded192_narrowings=325500"
  echo "cml_heap_mib=128"
  echo "cml_stack_mib=64"
  sha256sum "$trace_binary"
} > "$run_directory/manifest.txt"

printf 'run\twall_seconds\tuser_seconds\tsystem_seconds\tmaximum_rss_kib\texit\n' \
  > "$run_directory/runs.tsv"

# Untimed warm-up also validates the closed result and overflow checks.
CML_HEAP_SIZE=128 CML_STACK_SIZE=64 "$trace_binary"

for run in $(seq 1 "$runs"); do
  timing_file="$run_directory/.timing-$run"
  CML_HEAP_SIZE=128 CML_STACK_SIZE=64 \
    /usr/bin/time -f '%e\t%U\t%S\t%M\t%x' -o "$timing_file" "$trace_binary"
  printf '%s\t' "$run" >> "$run_directory/runs.tsv"
  cat "$timing_file" >> "$run_directory/runs.tsv"
  rm "$timing_file"
done

awk -F '\t' '
  NR > 1 {
    count += 1
    wall += $2
    user += $3
    sys_time += $4
    rss += $5
    if ($6 != 0) bad += 1
  }
  END {
    print "runs\tmean_wall_seconds\tmean_user_seconds\tmean_system_seconds\tmean_rss_kib\tnonzero_exits"
    printf "%d\t%.9f\t%.9f\t%.9f\t%.3f\t%d\n", count,
      wall / count, user / count, sys_time / count, rss / count, bad + 0
  }
' "$run_directory/runs.tsv" > "$run_directory/summary.tsv"

sha256sum "$run_directory/manifest.txt" "$run_directory/runs.tsv" \
  "$run_directory/summary.tsv" > "$run_directory/SHA256SUMS"

cat "$run_directory/summary.tsv"
