#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv EXPECTED.tsv OUTPUT-DIR\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
expected=$3
output_dir=$4
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
payload_verifier="$repo_root/scripts/verify-nl-case10173-angle-payloads.py"

[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]

g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 -DCANDLE_NL_FIXED_RANGE_PROFILE=1 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-int128-range"

"$output_dir/nl-native-int128-range" "$program" "$jobs" "$expected" \
  --specialized-angle-polynomials \
  --direct-delta-x4 \
  --skip-exact-zero-products \
  --symmetric-hessian-ops \
  --binary-scale-bits=23 \
  --fixed-sqrt-inverse-kernels \
  --fixed-atan-kernel \
  --prepared-simple-polynomials \
  --prepared-coordinate-sqrt-terms \
  --precompute-tight-sqrt-certificates \
  --dyadic-shift-fixed-quotient \
  --fuse-consecutive-adds \
  --count-fixed-quotients >"$output_dir/results.txt"

rg -q 'cells=4173 .*accepted=4173' "$output_dir/results.txt"
rg -q 'fixed_range_profile=1' "$output_dir/results.txt"
rg -q 'range_quotient_results_outside_int64=0' "$output_dir/results.txt"
rg -q 'range_multiplication_operands_outside_int64=0' \
  "$output_dir/results.txt"
rg -q 'range_addition_results_outside_int64=0' "$output_dir/results.txt"
rg -q 'range_scaled_inputs_outside_int64=0' "$output_dir/results.txt"
rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' "$output_dir/results.txt" \
  >"$output_dir/range-summary.txt"

sha256sum "$source_file" "$payload_verifier" "$program" "$jobs" \
  "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128-range" "$output_dir/results.txt" \
  "$output_dir/range-summary.txt" >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_FIXED_RANGE_PROFILE_OK DEVELOPMENT_NON_RELEASE'
