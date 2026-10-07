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
payload_verifier="$repo_root/scripts/verify-nl-case10173-angle-payloads.py"

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-int128"
build_end=$(date +%s%N)

options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --decimal-scale=10000000
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
  --precompute-tight-sqrt-certificates
  --delta-full-diagnostics
)

run_once() {
  local repetition=$1
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_(FIXED_SCALE_SUMMARY|DELTA_FULL_SUMMARY)' \
    | sed "s/$/ repetition=$repetition/"
}

run_once warmup >"$output_dir/warmup.txt"
: >"$output_dir/summaries.txt"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  run_once "$repetition" >>"$output_dir/summaries.txt"
done

"$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
  "${options[@]}" >"$output_dir/results.txt"
rg -q 'cells=4173 .*accepted=4173' "$output_dir/results.txt"
rg -q 'CANDLE_NL_NATIVE_DELTA_FULL_SUMMARY cells=4173 .*narrower_values=4173 .*narrower_gradients=25038 .*vertex_checks=267072' \
  "$output_dir/results.txt"

awk '
  /CANDLE_NL_NATIVE_DELTA_FULL_SUMMARY/ {
    generic = 0; candidate = 0; validation = 0; cells = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "cells") cells = field[2] + 0;
      if (field[1] == "generic_seconds") generic = field[2] + 0;
      if (field[1] == "candidate_seconds") candidate = field[2] + 0;
      if (field[1] == "validation_seconds") validation = field[2] + 0;
    }
    generic_sum += generic;
    candidate_sum += candidate;
    validation_sum += validation;
    count += 1;
    if (count == 1 || cells < minimum_cells) minimum_cells = cells;
  }
  END {
    g = generic_sum / count;
    c = candidate_sum / count;
    v = validation_sum / count;
    print "lane\trepetitions\tmean_seconds\tminimum_cells";
    printf "generic_delta_full\t%d\t%.9f\t%d\n", count, g, minimum_cells;
    printf "sign_directed_delta_full\t%d\t%.9f\t%d\n", count, c, minimum_cells;
    printf "development_validation\t%d\t%.9f\t%d\n", count, v, minimum_cells;
    printf "sign_directed_over_generic\t%d\t%.9f\t%d\n", count, c / g, minimum_cells;
  }
' "$output_dir/summaries.txt" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$source_file" "$payload_verifier" "$program" "$jobs" \
  "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$output_dir/warmup.txt" \
  "$output_dir/summaries.txt" "$output_dir/results.txt" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_DELTA_FULL_OK DEVELOPMENT_NON_RELEASE'
