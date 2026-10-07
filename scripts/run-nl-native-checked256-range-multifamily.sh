#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 8 ]]; then
  printf 'usage: %s CASE16594-PROGRAM CASE16594-JOBS CASE16594-EXPECTED CASE10173-PROGRAM CASE10173-JOBS CASE10173-EXPECTED OUTPUT-DIR LABEL\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
case16594_program=$1
case16594_jobs=$2
case16594_expected=$3
case10173_program=$4
case10173_jobs=$5
case10173_expected=$6
output_dir=$7
label=$8
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

for input in "$case16594_program" "$case16594_jobs" \
  "$case16594_expected" "$case10173_program" "$case10173_jobs" \
  "$case10173_expected" "$source_file"; do
  [[ -f "$input" ]]
done
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$case16594_jobs") -eq 875 ]]
[[ $(wc -l <"$case10173_jobs") -eq 4173 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

common=(
  -std=c++17 -O2 -Wall -Wextra -Werror
  -I"$boost_include"
  -DCANDLE_NL_CHECKED_INT256=1
  -DCANDLE_NL_FIXED_RANGE_PROFILE=1
)
g++ "${common[@]}" -DCANDLE_NL_CASE_ID=16594 \
  -DCANDLE_NL_SQRT_SLOTS=10 -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-range-case16594"
g++ "${common[@]}" "$source_file" -lgmpxx -lgmp \
  -o "$output_dir/nl-range-case10173"

run_lane() {
  local binary=$1 program=$2 jobs=$3 expected=$4 destination=$5
  shift 5
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M' \
    -o "$destination.resource.txt" \
    "$binary" "$program" "$jobs" "$expected" --accept-only "$@" \
    >"$destination.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY .*fixed_range_profile=1' \
    "$destination.txt"
}

run_lane "$output_dir/nl-range-case16594" "$case16594_program" \
  "$case16594_jobs" "$case16594_expected" \
  "$output_dir/case16594-decimal"
run_lane "$output_dir/nl-range-case16594" "$case16594_program" \
  "$case16594_jobs" "$case16594_expected" \
  "$output_dir/case16594-dyadic" --binary-scale-bits=40 \
  --dyadic-shift-fixed-quotient

case10173_options=(
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
  --computed-tight-sqrt-certificates
  --specialized-angle-polynomials
  --direct-delta-x4
)
run_lane "$output_dir/nl-range-case10173" "$case10173_program" \
  "$case10173_jobs" "$case10173_expected" \
  "$output_dir/case10173-decimal" --decimal-scale=10000000000 \
  "${case10173_options[@]}"
run_lane "$output_dir/nl-range-case10173" "$case10173_program" \
  "$case10173_jobs" "$case10173_expected" \
  "$output_dir/case10173-dyadic" --binary-scale-bits=23 \
  --dyadic-shift-fixed-quotient "${case10173_options[@]}"

rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=checked-int256 .*arithmetic=decimal-1e12 .*case_id=16594 .*accepted=875' \
  "$output_dir/case16594-decimal.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=checked-int256 .*arithmetic=dyadic .*case_id=16594 .*accepted=875' \
  "$output_dir/case16594-dyadic.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=4173 .*backend=checked-int256 .*arithmetic=decimal-custom .*case_id=10173 .*accepted=4173' \
  "$output_dir/case10173-decimal.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=4173 .*backend=checked-int256 .*arithmetic=dyadic .*case_id=10173 .*accepted=4173' \
  "$output_dir/case10173-dyadic.txt"

{
  printf 'lane\tquotient_numerator_bits\tquotient_denominator_bits\tquotient_result_bits\tmultiplication_operand_bits\tmultiplication_product_bits\taddition_result_bits\tscaled_input_bits\taccepted\n'
  for lane in case16594-decimal case16594-dyadic \
              case10173-decimal case10173-dyadic; do
    awk -v lane="$lane" '
      /^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
        qn = qd = qr = mo = mp = ar = si = accepted = 0;
        for (i = 1; i <= NF; ++i) {
          split($i, field, "=");
          if (field[1] == "range_quotient_numerator_bits") qn = field[2];
          if (field[1] == "range_quotient_denominator_bits") qd = field[2];
          if (field[1] == "range_quotient_result_bits") qr = field[2];
          if (field[1] == "range_multiplication_operand_bits") mo = field[2];
          if (field[1] == "range_multiplication_product_bits") mp = field[2];
          if (field[1] == "range_addition_result_bits") ar = field[2];
          if (field[1] == "range_scaled_input_bits") si = field[2];
          if (field[1] == "accepted") accepted = field[2];
        }
        printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", lane,
               qn, qd, qr, mo, mp, ar, si, accepted;
      }
    ' "$output_dir/$lane.txt"
  done
} >"$output_dir/range-summary.tsv"

{
  printf 'lane\tscalar_dot_product_bits\tscalar_dot_accumulator_bits\tscalar_radius_product_bits\tscalar_weighted_product_bits\tscalar_weighted_accumulator_bits\ttaylor_error_product_bits\ttaylor_error_bits\ttaylor_center_product_bits\ttaylor_center_raw_bits\ttaylor_gradient_product_bits\ttaylor_gradient_raw_bits\tscalar_dot_terms\tscalar_weighted_terms\ttaylor_completion_calls\ttaylor_gradient_bound_endpoints\taccepted\n'
  for lane in case16594-decimal case16594-dyadic \
              case10173-decimal case10173-dyadic; do
    awk -v lane="$lane" '
      /^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
        for (i = 1; i <= NF; ++i) {
          split($i, field, "=");
          value[field[1]] = field[2];
        }
        printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", lane,
          value["range_scalar_dot_product_bits"],
          value["range_scalar_dot_accumulator_bits"],
          value["range_scalar_radius_product_bits"],
          value["range_scalar_weighted_product_bits"],
          value["range_scalar_weighted_accumulator_bits"],
          value["range_taylor_error_product_bits"],
          value["range_taylor_error_bits"],
          value["range_taylor_center_product_bits"],
          value["range_taylor_center_raw_bits"],
          value["range_taylor_gradient_product_bits"],
          value["range_taylor_gradient_raw_bits"],
          value["range_scalar_dot_terms"],
          value["range_scalar_weighted_terms"],
          value["range_taylor_completion_calls"],
          value["range_taylor_gradient_bound_endpoints"],
          value["accepted"];
      }
    ' "$output_dir/$lane.txt"
  done
} >"$output_dir/operation-ledger.tsv"

sha256sum "$0" "$source_file" "$case16594_program" "$case16594_jobs" \
  "$case16594_expected" "$case10173_program" "$case10173_jobs" \
  "$case10173_expected" "$output_dir"/*.txt \
  "$output_dir/range-summary.tsv" "$output_dir/operation-ledger.tsv" \
  >"$output_dir/result-files.sha256"
printf 'CANDLE_NL_NATIVE_CHECKED256_RANGE_MULTIFAMILY_OK %s DEVELOPMENT_NON_RELEASE\n' \
  "$label"
