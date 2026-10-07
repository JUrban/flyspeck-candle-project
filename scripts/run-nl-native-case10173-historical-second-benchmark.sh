#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv EXPECTED.tsv OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
expected=$3
output_dir=$4
repetitions=$5
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-historical-second-mpz"
build_end=$(date +%s%N)

/usr/bin/time -v -o "$output_dir/time.txt" \
  "$output_dir/nl-native-historical-second-mpz" \
  "$program" "$jobs" "$expected" \
  --specialized-angle-polynomials \
  --direct-delta-x4 \
  --skip-exact-zero-products \
  --symmetric-hessian-ops \
  --fixed-sqrt-inverse-kernels \
  --fixed-atan-kernel \
  --prepared-simple-polynomials \
  --prepared-coordinate-sqrt-terms \
  --precompute-tight-sqrt-certificates \
  --historical-dihedral \
  --historical-block-rounding \
  --historical-center-tangent \
  "--historical-second-benchmark-repetitions=$repetitions" \
  >"$output_dir/native.log" 2>"$output_dir/stderr.txt"

rg -q 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=128 .*accepted=128' \
  "$output_dir/native.log"
rg -q "CANDLE_NL_NATIVE_HISTORICAL_SECOND_BENCHMARK cells=128 repetitions=$repetitions .*evaluation_sqrt_steps=0" \
  "$output_dir/native.log"
[[ ! -s "$output_dir/stderr.txt" ]]

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/nl-native-historical-second-mpz" \
  "$output_dir/native.log" "$output_dir/stderr.txt" \
  "$output_dir/time.txt" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_HISTORICAL_SECOND_BENCHMARK_OK DEVELOPMENT_NON_RELEASE'
