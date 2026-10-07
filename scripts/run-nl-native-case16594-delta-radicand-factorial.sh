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
for input in "$program" "$jobs" "$expected" "$source_file"; do
  [[ -f "$input" ]]
done
[[ -x "$bound_analyzer" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

common=(-std=c++17 -O2 -Wall -Wextra -Werror)
defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)

build_begin=$(date +%s%N)
g++ "${common[@]}" -I"$boost_include" -DCANDLE_NL_MIXED_INT128_192=1 \
  "${defines[@]}" "$source_file" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-mixed"
build_mixed_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_DOUBLE=1 "${defines[@]}" \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-double"
build_double_end=$(date +%s%N)

summaries="$output_dir/summaries.txt"
: >"$summaries"

lane_options() {
  local lane=$1
  case "$lane" in
    exact-baseline)
      printf '%s\0' --accept-only --count-fixed-quotients \
        --binary-scale-bits=40 --dyadic-shift-fixed-quotient
      ;;
    exact-specialized)
      printf '%s\0' --accept-only --count-fixed-quotients \
        --binary-scale-bits=40 --dyadic-shift-fixed-quotient \
        --specialized-delta-radicands
      ;;
    double-baseline)
      printf '%s\0' --accept-only --count-fixed-quotients \
        --binary-scale-bits=40
      ;;
    double-specialized)
      printf '%s\0' --accept-only --count-fixed-quotients \
        --binary-scale-bits=40 --specialized-delta-radicands
      ;;
    *)
      printf 'unknown lane: %s\n' "$lane" >&2
      exit 2
      ;;
  esac
}

run_lane() {
  local lane=$1 repetition=$2 destination=$3 binary
  local -a options
  mapfile -d '' -t options < <(lane_options "$lane")
  case "$lane" in
    exact-*) binary="$output_dir/nl-native-mixed" ;;
    double-*) binary="$output_dir/nl-native-double" ;;
  esac
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(exact-baseline exact-specialized double-baseline double-specialized)
for lane in "${lanes[@]}"; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

for lane in "${lanes[@]}"; do
  case "$lane" in
    exact-*) binary="$output_dir/nl-native-mixed" ;;
    double-*) binary="$output_dir/nl-native-double" ;;
  esac
  mapfile -d '' -t options < <(lane_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M' \
    -o "$output_dir/$lane-resource.txt" \
    "$binary" "$program" "$jobs" "$expected" "${options[@]}" \
    >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-summary.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*accepted=875' \
    "$output_dir/$lane-summary.txt"
  if [[ "$lane" == *-specialized ]]; then
    rg -q ' specialized_delta_radicands=1 specialized_delta_radicand_count=3 ' \
      "$output_dir/$lane-summary.txt"
  else
    rg -q ' specialized_delta_radicands=0 specialized_delta_radicand_count=0 ' \
      "$output_dir/$lane-summary.txt"
  fi
done

"$bound_analyzer" "$output_dir/exact-baseline-results.txt" \
  "$output_dir/exact-specialized-results.txt" \
  >"$output_dir/exact-specialized-vs-baseline-bounds.json"
"$bound_analyzer" "$output_dir/double-baseline-results.txt" \
  "$output_dir/double-specialized-results.txt" \
  >"$output_dir/double-specialized-vs-baseline-bounds.json"
"$bound_analyzer" "$output_dir/exact-specialized-results.txt" \
  "$output_dir/double-specialized-results.txt" \
  >"$output_dir/double-vs-exact-specialized-bounds.json"

awk '
  function field_value(name,   idx, pair) {
    for (idx = 1; idx <= NF; ++idx) {
      split($idx, pair, "=")
      if (pair[1] == name) return pair[2]
    }
    return ""
  }
  {
    lane = field_value("lane")
    if (field_value("repetition") == "warmup" || lane == "") next
    count[lane]++
    preparation[lane] += field_value("preparation_seconds")
    evaluation[lane] += field_value("evaluation_seconds")
    accepted = field_value("accepted") + 0
    if (!(lane in minimum_accepted) || accepted < minimum_accepted[lane]) {
      minimum_accepted[lane] = accepted
    }
  }
  END {
    print "lane\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted"
    lanes[1] = "exact-baseline"
    lanes[2] = "exact-specialized"
    lanes[3] = "double-baseline"
    lanes[4] = "double-specialized"
    for (lane_index = 1; lane_index <= 4; ++lane_index) {
      lane = lanes[lane_index]
      mean_preparation = preparation[lane] / count[lane]
      mean_evaluation = evaluation[lane] / count[lane]
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane],
        mean_preparation, mean_evaluation,
        mean_preparation + mean_evaluation, minimum_accepted[lane]
    }
    exact_baseline = evaluation["exact-baseline"] / count["exact-baseline"]
    exact_specialized = evaluation["exact-specialized"] / count["exact-specialized"]
    double_baseline = evaluation["double-baseline"] / count["double-baseline"]
    double_specialized = evaluation["double-specialized"] / count["double-specialized"]
    printf "exact_specialization_speedup\t%d\t0\t%.9f\t0\t875\n", count["exact-specialized"], exact_baseline / exact_specialized
    printf "double_specialization_speedup\t%d\t0\t%.9f\t0\t875\n", count["double-specialized"], double_baseline / double_specialized
    printf "baseline_exact_over_double\t%d\t0\t%.9f\t0\t875\n", count["exact-baseline"], exact_baseline / double_baseline
    printf "specialized_exact_over_double\t%d\t0\t%.9f\t0\t875\n", count["exact-specialized"], exact_specialized / double_specialized
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v mixed="$build_mixed_end" \
    -v double="$build_double_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_mixed\t%.9f\n", (mixed - begin) / 1000000000
  printf "build_double\t%.9f\n", (double - mixed) / 1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/nl-native-mixed" "$output_dir/nl-native-double" \
  "$output_dir/summaries.txt" "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" \
  "$output_dir/exact-specialized-vs-baseline-bounds.json" \
  "$output_dir/double-specialized-vs-baseline-bounds.json" \
  "$output_dir/double-vs-exact-specialized-bounds.json" \
  >"$output_dir/result-files.sha256"

cat "$output_dir/phase-times.tsv"
