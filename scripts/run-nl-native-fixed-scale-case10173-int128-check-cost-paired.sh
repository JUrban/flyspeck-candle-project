#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  printf 'usage: %s NATIVE-INPUT-RUN-DIR OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
input_dir=$1
output_dir=$2
repetitions=$3
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
payload_verifier="$repo_root/scripts/verify-nl-case10173-angle-payloads.py"
program="$input_dir/case10173-program.cval"
jobs="$input_dir/case10173-native-jobs-prefix128.tsv"
expected=/project/flyspeck-candle-runs/cv-case10173-bound-tightness-prefix128-v3-16g-dev-001/case10173-reflected-bounds-prefix128.tsv
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
comparison_scale=10000000000

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$source_file" ]]
[[ -x "$payload_verifier" ]]
[[ -f "$program" ]]
[[ -f "$jobs" ]]
[[ -f "$expected" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"

total_begin=$(date +%s%N)
build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 -I"$boost_include" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-int128"
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_CHECKED_INT128=1 -I"$boost_include" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-checked128"
build_end=$(date +%s%N)

common_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --decimal-scale="$comparison_scale"
)

summaries="$output_dir/summaries.txt"
: >"$summaries"

run_lane() {
  local backend=$1
  local repetition=$2
  "$output_dir/nl-native-fixed-scale-$backend" \
    "$program" "$jobs" "$expected" "${common_options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ repetition=$repetition/" >>"$summaries"
}

run_lane int128 warmup
run_lane checked128 warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane int128 "$repetition"
    run_lane checked128 "$repetition"
  else
    run_lane checked128 "$repetition"
    run_lane int128 "$repetition"
  fi
done

"$output_dir/nl-native-fixed-scale-int128" \
  "$program" "$jobs" "$expected" "${common_options[@]}" \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/int128-results.txt"
"$output_dir/nl-native-fixed-scale-checked128" \
  "$program" "$jobs" "$expected" "${common_options[@]}" \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/checked128-results.txt"
cmp "$output_dir/int128-results.txt" "$output_dir/checked128-results.txt"
total_end=$(date +%s%N)

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    backend = "";
    preparation = 0;
    seconds = 0;
    accepted = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "backend") backend = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") seconds = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    sum[backend] += seconds;
    preparation_sum[backend] += preparation;
    count[backend] += 1;
    if (accepted < min_accepted[backend] || count[backend] == 1) {
      min_accepted[backend] = accepted;
    }
  }
  END {
    unchecked = sum["int128"] / count["int128"];
    checked = sum["checked-int128"] / count["checked-int128"];
    unchecked_preparation = preparation_sum["int128"] / count["int128"];
    checked_preparation = preparation_sum["checked-int128"] / count["checked-int128"];
    print "backend\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tmin_accepted";
    printf "native-int128-unchecked\t%d\t%.9f\t%.9f\t%.9f\t%d\n",
      count["int128"], unchecked_preparation, unchecked,
      unchecked_preparation + unchecked, min_accepted["int128"];
    printf "boost-int128-checked\t%d\t%.9f\t%.9f\t%.9f\t%d\n",
      count["checked-int128"], checked_preparation, checked,
      checked_preparation + checked, min_accepted["checked-int128"];
    printf "unchecked-evaluation-speedup\t%d\t0\t%.9f\t0\t%d\n",
      count["int128"], checked / unchecked, min_accepted["int128"];
    printf "unchecked-batch-speedup\t%d\t0\t0\t%.9f\t%d\n",
      count["int128"],
      (checked_preparation + checked) / (unchecked_preparation + unchecked),
      min_accepted["int128"];
    printf "evaluation-time-reduction-percent\t%d\t0\t%.6f\t0\t%d\n",
      count["int128"], 100 * (checked - unchecked) / checked,
      min_accepted["int128"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" \
    -v total_begin="$total_begin" -v total_end="$total_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build\t%.9f\n", (build_end - build_begin) / 1000000000;
    printf "total\t%.9f\n", (total_end - total_begin) / 1000000000;
  }
' >"$output_dir/wall-times.tsv"

sha256sum "$source_file" "$payload_verifier" "$program" "$jobs" \
  "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-fixed-scale-int128" \
  "$output_dir/nl-native-fixed-scale-checked128" "$summaries" \
  "$output_dir/phase-times.tsv" "$output_dir/wall-times.tsv" \
  "$output_dir/int128-results.txt" "$output_dir/checked128-results.txt" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_INT128_CHECK_COST_PAIRED_OK DEVELOPMENT_NON_RELEASE'
