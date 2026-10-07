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
  -DCANDLE_NL_FIXED_INT128=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-int128"

common_options=(
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
  --count-fixed-quotients
)

for lane in generic historical-block; do
  options=("${common_options[@]}")
  if [[ "$lane" == historical-block ]]; then
    options+=(--historical-dihedral --historical-block-rounding)
  fi
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
  rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    "$output_dir/$lane-results.txt" \
    | sed "s/$/ lane=$lane/" >>"$output_dir/summaries.txt"
done

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; cells = 0; pf = 0; pc = 0; ef = 0; ec = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "cells") cells = field[2] + 0;
      if (field[1] == "preparation_floor_quotients") pf = field[2] + 0;
      if (field[1] == "preparation_ceil_quotients") pc = field[2] + 0;
      if (field[1] == "evaluation_floor_quotients") ef = field[2] + 0;
      if (field[1] == "evaluation_ceil_quotients") ec = field[2] + 0;
    }
    evaluation[lane] = ef + ec;
    print lane "\t" cells "\t" pf + pc "\t" ef + ec "\t" (ef + ec) / cells;
  }
  END {
    print "historical_over_generic\t0\t0\t" evaluation["historical-block"] / evaluation["generic"] "\t0";
  }
' "$output_dir/summaries.txt" \
  | { printf 'lane\tcells\tpreparation_quotients\tevaluation_quotients\tevaluation_quotients_per_cell\n'; cat; } \
  >"$output_dir/quotient-counts.tsv"

sha256sum "$source_file" "$payload_verifier" "$program" "$jobs" \
  "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$output_dir/generic-results.txt" \
  "$output_dir/historical-block-results.txt" \
  "$output_dir/summaries.txt" "$output_dir/quotient-counts.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_ROUNDING_COUNTS_OK DEVELOPMENT_NON_RELEASE'
