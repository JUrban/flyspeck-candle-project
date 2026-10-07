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
bound_analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ -x "$bound_analyzer" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

common_defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_CHECKED_INT256=1 "${common_defines[@]}" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-checked256"
build_checked256_end=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_DOUBLE=1 "${common_defines[@]}" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-double"
build_double_end=$(date +%s%N)

summaries="$output_dir/summaries.txt"
: >"$summaries"

run_lane() {
  local lane=$1 repetition=$2 destination=$3 binary
  local -a options=(--accept-only --count-fixed-quotients)
  case "$lane" in
    checked-decimal)
      binary="$output_dir/nl-native-checked256"
      ;;
    checked-dyadic)
      binary="$output_dir/nl-native-checked256"
      options+=(--binary-scale-bits=40 --dyadic-shift-fixed-quotient)
      ;;
    padded-double)
      binary="$output_dir/nl-native-double"
      ;;
    *)
      printf 'unknown lane: %s\n' "$lane" >&2
      exit 2
      ;;
  esac
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(checked-decimal checked-dyadic padded-double)
for lane in "${lanes[@]}"; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

"$output_dir/nl-native-checked256" "$program" "$jobs" "$expected" \
  --count-fixed-quotients >"$output_dir/checked-decimal-results.txt"
"$output_dir/nl-native-checked256" "$program" "$jobs" "$expected" \
  --accept-only --count-fixed-quotients --binary-scale-bits=40 \
  --dyadic-shift-fixed-quotient >"$output_dir/checked-dyadic-results.txt"
"$output_dir/nl-native-double" "$program" "$jobs" "$expected" \
  --accept-only --count-fixed-quotients \
  >"$output_dir/padded-double-results.txt"
"$output_dir/nl-native-checked256" "$program" "$jobs" "$expected" \
  --accept-only --profile --binary-scale-bits=40 \
  --dyadic-shift-fixed-quotient \
  >"$output_dir/checked-dyadic-profile.txt"
"$output_dir/nl-native-double" "$program" "$jobs" "$expected" \
  --accept-only --profile >"$output_dir/padded-double-profile.txt"

rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=checked-int256 .*arithmetic=decimal-1e12 .*case_id=16594 .*matched=875 .*accepted=875' \
  "$output_dir/checked-decimal-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=checked-int256 .*arithmetic=dyadic .*binary_scale_bits=40 .*dyadic_shift_fixed_quotient=1 .*case_id=16594 .*accepted=875' \
  "$output_dir/checked-dyadic-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=double-integer .*case_id=16594 .*accepted=875' \
  "$output_dir/padded-double-results.txt"
rg -q 'evaluation_dyadic_shift_quotients=20620250 evaluation_dyadic_fallback_quotients=0' \
  "$output_dir/checked-dyadic-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=checked-int256 .*arithmetic=dyadic .*case_id=16594 .*accepted=875' \
  "$output_dir/checked-dyadic-profile.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=double-integer .*case_id=16594 .*accepted=875' \
  "$output_dir/padded-double-profile.txt"

"$bound_analyzer" "$output_dir/checked-decimal-results.txt" \
  "$output_dir/checked-dyadic-results.txt" \
  >"$output_dir/dyadic-vs-decimal-bounds.json"
"$bound_analyzer" "$output_dir/checked-dyadic-results.txt" \
  "$output_dir/padded-double-results.txt" \
  >"$output_dir/double-vs-dyadic-bounds.json"

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = evaluation = accepted = 0;
    for (i = 1; i <= NF; ++i) {
      split($i, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    count[lane]++;
    if (count[lane] == 1 || accepted < minimum_accepted[lane])
      minimum_accepted[lane] = accepted;
  }
  END {
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    lanes[1] = "checked-decimal";
    lanes[2] = "checked-dyadic";
    lanes[3] = "padded-double";
    for (j = 1; j <= 3; ++j) {
      lane = lanes[j];
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane], p, e, p + e, minimum_accepted[lane];
    }
    decimal = evaluation_sum["checked-decimal"] / count["checked-decimal"];
    dyadic = evaluation_sum["checked-dyadic"] / count["checked-dyadic"];
    hardware = evaluation_sum["padded-double"] / count["padded-double"];
    printf "checked_decimal_over_dyadic_evaluation\t%d\t0\t%.9f\t0\t0\n", count["checked-decimal"], decimal / dyadic;
    printf "checked_dyadic_over_padded_double_evaluation\t%d\t0\t%.9f\t0\t0\n", count["checked-decimal"], dyadic / hardware;
    printf "checked_decimal_over_padded_double_evaluation\t%d\t0\t%.9f\t0\t0\n", count["checked-decimal"], decimal / hardware;
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v checked="$build_checked256_end" \
    -v double="$build_double_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_checked256\t%.9f\n", (checked - begin) / 1000000000;
    printf "build_double\t%.9f\n", (double - checked) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

{
  printf 'lane\tlabel\ttotal_nanoseconds\tinterval_products\tinstructions\n'
  for lane in checked-dyadic padded-double; do
    awk -v lane="$lane" '
      /^CANDLE_NL_NATIVE_FIXED_SCALE_PROFILE/ {
        label = ""; nanoseconds = products = 0;
        for (i = 1; i <= NF; ++i) {
          split($i, field, "=");
          if (field[1] == "label") label = field[2];
          if (field[1] == "nanoseconds") nanoseconds = field[2] + 0;
          if (field[1] == "interval_products") products = field[2] + 0;
        }
        time[label] += nanoseconds;
        product_count[label] += products;
        instruction_count[label]++;
      }
      END {
        for (label in time) {
          printf "%s\t%s\t%.0f\t%.0f\t%d\n", lane, label, time[label],
                 product_count[label], instruction_count[label];
        }
      }
    ' "$output_dir/$lane-profile.txt"
  done
} >"$output_dir/instruction-profile-summary.tsv"

sha256sum "$0" "$source_file" "$bound_analyzer" "$program" "$jobs" \
  "$expected" "$output_dir/summaries.txt" \
  "$output_dir/checked-decimal-results.txt" \
  "$output_dir/checked-dyadic-results.txt" \
  "$output_dir/padded-double-results.txt" \
  "$output_dir/checked-dyadic-profile.txt" \
  "$output_dir/padded-double-profile.txt" \
  "$output_dir/dyadic-vs-decimal-bounds.json" \
  "$output_dir/double-vs-dyadic-bounds.json" \
  "$output_dir/instruction-profile-summary.tsv" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_CHECKED_ROUNDING_PAIRED_OK DEVELOPMENT_NON_RELEASE'
