#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "usage: $0 DECIMAL_BINARY BINARY_DIRECTORY RUN_DIRECTORY [PAIRS]" >&2
  exit 2
fi

decimal_binary=$1
binary_directory=$2
run_directory=$3
pairs=${4:-7}

shift_binary="$binary_directory/compute_bounded_mul_shift40_benchmark"
control_binary="$binary_directory/compute_bounded_mul_control_benchmark"

[[ -x "$decimal_binary" ]] || { echo "missing executable: $decimal_binary" >&2; exit 2; }
[[ -x "$shift_binary" ]] || { echo "missing executable: $shift_binary" >&2; exit 2; }
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
  echo "decimal_scale=1000000000000"
  echo "dyadic_floor_shift_bits=40"
  echo "cml_heap_mib=128"
  echo "cml_stack_mib=64"
  sha256sum "$decimal_binary" "$shift_binary" "$control_binary"
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

# Untimed warm-up also validates each executable's internal result check.
CML_HEAP_SIZE=128 CML_STACK_SIZE=64 "$decimal_binary"
CML_HEAP_SIZE=128 CML_STACK_SIZE=64 "$shift_binary"
CML_HEAP_SIZE=128 CML_STACK_SIZE=64 "$control_binary"

for pair in $(seq 1 "$pairs"); do
  case $((pair % 3)) in
    1)
      run_lane "$pair" 1 decimal "$decimal_binary"
      run_lane "$pair" 2 shift40 "$shift_binary"
      run_lane "$pair" 3 control "$control_binary"
      ;;
    2)
      run_lane "$pair" 1 shift40 "$shift_binary"
      run_lane "$pair" 2 control "$control_binary"
      run_lane "$pair" 3 decimal "$decimal_binary"
      ;;
    0)
      run_lane "$pair" 1 control "$control_binary"
      run_lane "$pair" 2 decimal "$decimal_binary"
      run_lane "$pair" 3 shift40 "$shift_binary"
      ;;
  esac
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
    order[1] = "decimal"
    order[2] = "shift40"
    order[3] = "control"
    for (idx = 1; idx <= 3; idx++) {
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
