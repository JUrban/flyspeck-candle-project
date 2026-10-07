#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 || $# -gt 5 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv EXPECTED.tsv OUTPUT-DIR [decimal|composed]\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
expected=$3
output_dir=$4
mode=${5:-decimal}
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
payload_verifier="$repo_root/scripts/verify-nl-case10173-angle-payloads.py"

[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" ]]
[[ ! -e "$output_dir" ]]
[[ "$mode" == decimal || "$mode" == composed ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]

g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-int128"

options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
  --precompute-tight-sqrt-certificates
  --rounding-profile
)
if [[ "$mode" == decimal ]]; then
  options+=(--decimal-scale=10000000)
else
  options+=(
    --binary-scale-bits=23
    --dyadic-shift-fixed-quotient
    --fuse-consecutive-adds
  )
fi
"$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
  "${options[@]}" >"$output_dir/results.txt"

rg -q 'cells=4173 .*accepted=4173' "$output_dir/results.txt"
rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' "$output_dir/results.txt" \
  >"$output_dir/summary.txt"
rg 'CANDLE_NL_NATIVE_FIXED_SCALE_ROUNDING_PROFILE' \
  "$output_dir/results.txt" >"$output_dir/profile-records.txt"

awk '
  BEGIN {
    print "index\tlabel\tobservations\tnanoseconds\tfloor_quotients\tceil_quotients\ttotal_quotients";
  }
  {
    instruction_index = ""; label = ""; observations = 0;
    nanoseconds = 0; floor_quotients = 0; ceil_quotients = 0;
    total_quotients = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "index") instruction_index = field[2];
      if (field[1] == "label") label = field[2];
      if (field[1] == "observations") observations = field[2] + 0;
      if (field[1] == "nanoseconds") nanoseconds = field[2] + 0;
      if (field[1] == "floor_quotients") floor_quotients = field[2] + 0;
      if (field[1] == "ceil_quotients") ceil_quotients = field[2] + 0;
      if (field[1] == "total_quotients") total_quotients = field[2] + 0;
    }
    print instruction_index "\t" label "\t" observations "\t" nanoseconds \
          "\t" floor_quotients "\t" ceil_quotients "\t" total_quotients;
  }
' "$output_dir/profile-records.txt" >"$output_dir/profile.tsv"

awk -F '\t' '
  NR == 1 { next }
  { nanoseconds[$2] += $4; quotients[$2] += $7 }
  END {
    print "label\ttotal_nanoseconds\ttotal_quotients";
    for (label in nanoseconds) {
      print label "\t" nanoseconds[label] "\t" quotients[label];
    }
  }
' "$output_dir/profile.tsv" \
  | { IFS= read -r header; printf '%s\n' "$header"; sort -t $'\t' -k2,2nr; } \
  >"$output_dir/profile-by-label.tsv"

sha256sum "$source_file" "$payload_verifier" "$program" "$jobs" \
  "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$output_dir/results.txt" \
  "$output_dir/summary.txt" "$output_dir/profile-records.txt" \
  "$output_dir/profile.tsv" "$output_dir/profile-by-label.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_ROUNDING_PROFILE_OK DEVELOPMENT_NON_RELEASE'
