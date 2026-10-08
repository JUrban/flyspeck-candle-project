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
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

for input in "$program" "$jobs" "$expected" "$source_file"; do
  [[ -f "$input" ]]
done
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_FIXED_INT128=1 \
  -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 \
  -DCANDLE_NL_CASE_ID=16594 -DCANDLE_NL_SQRT_SLOTS=10 \
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-builtin"

common_options=(
  --accept-only
  --count-fixed-quotients
  --binary-scale-bits=40
  --dyadic-shift-fixed-quotient
  --sign-specialized-interval-products
  --specialized-delta-radicands
  --specialized-delta-derivatives
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
)

for repetition in first second; do
  certificates="$output_dir/analytic-certificates-$repetition.tsv"
  "$output_dir/nl-native-builtin" "$program" "$jobs" "$expected" \
    "${common_options[@]}" \
    --capture-analytic-certificates="$certificates" \
    >"$output_dir/results-$repetition.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    "$output_dir/results-$repetition.txt" \
    >"$output_dir/summary-$repetition.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*fixed_sqrt_inverse_kernels=1 .*fixed_atan_kernel=1 .*analytic_certificate_capture=1 analytic_certificate_records=27125 .*accepted=875' \
    "$output_dir/summary-$repetition.txt"
  [[ $(wc -l <"$certificates") -eq 27125 ]]
done

cmp "$output_dir/analytic-certificates-first.tsv" \
  "$output_dir/analytic-certificates-second.tsv"

awk -F '\t' '
  BEGIN { expected_job = 0; expected_ordinal = 0 }
  {
    if (NF != 15 || $1 != expected_job || $2 != expected_ordinal) bad++
    kinds[$3]++
    lower += $4
    upper += $5
    expected_ordinal++
    if (expected_ordinal == 31) {
      expected_job++
      expected_ordinal = 0
    }
  }
  END {
    if (NR != 27125 || expected_job != 875 || expected_ordinal != 0 ||
        bad != 0 || kinds["sqrt"] != 8750 ||
        kinds["inverse"] != 12250 || kinds["atan"] != 6125 ||
        lower != 107 || upper != 107) exit 1
    print "rows\tjobs\tsqrt\tinverse\tatan\tlower_range\tupper_range"
    printf "%d\t%d\t%d\t%d\t%d\t%d\t%d\n", NR, expected_job,
      kinds["sqrt"], kinds["inverse"], kinds["atan"], lower, upper
  }
' "$output_dir/analytic-certificates-first.tsv" \
  >"$output_dir/certificate-shape.tsv"

sha256sum \
  "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/analytic-certificates-first.tsv" \
  "$output_dir/summary-first.txt" \
  >"$output_dir/result-files.sha256"

printf 'status=DEVELOPMENT_NON_RELEASE\n' >"$output_dir/decision.txt"
printf 'cells=875\nrecords_per_cell=31\nrecords=27125\n' \
  >>"$output_dir/decision.txt"
printf 'accepted=875/875\nrepeat_byte_identical=yes\n' \
  >>"$output_dir/decision.txt"
