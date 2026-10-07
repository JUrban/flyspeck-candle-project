#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: $0 BINARY_DIRECTORY RUN_DIRECTORY [PAIRS]" >&2
  exit 2
fi

binary_directory=$1
run_directory=$2
pairs=${3:-7}

mul_binary="$binary_directory/compute_bounded_mul_chunks22_benchmark"
control_binary="$binary_directory/compute_bounded_mul_control_benchmark"

[[ -x "$mul_binary" ]] || { echo "missing executable: $mul_binary" >&2; exit 2; }
[[ -x "$control_binary" ]] || { echo "missing executable: $control_binary" >&2; exit 2; }
[[ "$pairs" =~ ^[1-9][0-9]*$ ]] || { echo "PAIRS must be positive" >&2; exit 2; }

mkdir "$run_directory"

{
  echo "status=DEVELOPMENT_NON_RELEASE"
  echo "issued_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "pairs=$pairs"
  echo "iterations_per_run=10000001"
  echo "left_operand=4503599627370453"
  echo "right_operand=1099511627689"
  echo "exact_product_bits=92"
  echo "chunk_radix_bits=22"
  echo "chunk_products=9"
  echo "cml_heap_mib=128"
  echo "cml_stack_mib=64"
  sha256sum "$mul_binary" "$control_binary"
} > "$run_directory/manifest.txt"

printf 'pair\tposition\tlane\twall_seconds\tuser_seconds\tsystem_seconds\tmaximum_rss_kib\texit\n' \
  > "$run_directory/runs.tsv"

run_lane() {
  local pair=$1
  local position=$2
  local lane=$3
  local binary=$4
  local timing_file="$run_directory/.timing-${pair}-${position}-${lane}"

  CML_HEAP_SIZE=128 CML_STACK_SIZE=64 \
    /usr/bin/time -f '%e\t%U\t%S\t%M\t%x' -o "$timing_file" "$binary"
  printf '%s\t%s\t%s\t' "$pair" "$position" "$lane" >> "$run_directory/runs.tsv"
  cat "$timing_file" >> "$run_directory/runs.tsv"
  rm "$timing_file"
}

# Untimed warm-up validates both observable result checks before collection.
CML_HEAP_SIZE=128 CML_STACK_SIZE=64 "$mul_binary"
CML_HEAP_SIZE=128 CML_STACK_SIZE=64 "$control_binary"

for pair in $(seq 1 "$pairs"); do
  if (( pair % 2 == 1 )); then
    run_lane "$pair" 1 chunks22 "$mul_binary"
    run_lane "$pair" 2 control "$control_binary"
  else
    run_lane "$pair" 1 control "$control_binary"
    run_lane "$pair" 2 chunks22 "$mul_binary"
  fi
done

awk -F '\t' '
  NR > 1 {
    count[$3] += 1
    wall[$3] += $4
    user[$3] += $5
    sys_time[$3] += $6
    rss[$3] += $7
    if ($8 != 0) bad[$3] += 1
  }
  END {
    print "lane\truns\tmean_wall_seconds\tmean_user_seconds\tmean_system_seconds\tmean_rss_kib\tnonzero_exits"
    order[1] = "chunks22"
    order[2] = "control"
    for (idx = 1; idx <= 2; idx++) {
      lane = order[idx]
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.3f\t%d\n", lane, count[lane],
        wall[lane] / count[lane], user[lane] / count[lane],
        sys_time[lane] / count[lane], rss[lane] / count[lane], bad[lane] + 0
    }
  }
' "$run_directory/runs.tsv" > "$run_directory/summary.tsv"

sha256sum "$run_directory/manifest.txt" "$run_directory/runs.tsv" \
  "$run_directory/summary.tsv" > "$run_directory/SHA256SUMS"

cat "$run_directory/summary.tsv"
