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

run_lane() {
  local lane=$1 repetition=$2 destination=$3 binary
  local -a options=(--accept-only --count-fixed-quotients \
    --binary-scale-bits=40)
  case "$lane" in
    exact-baseline)
      binary="$output_dir/nl-native-mixed"
      options+=(--dyadic-shift-fixed-quotient)
      ;;
    exact-fused39)
      binary="$output_dir/nl-native-mixed"
      options+=(--dyadic-shift-fixed-quotient \
        --fused-polynomial-max-steps=39)
      ;;
    double-baseline)
      binary="$output_dir/nl-native-double"
      ;;
    double-fused39)
      binary="$output_dir/nl-native-double"
      options+=(--fused-polynomial-max-steps=39)
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

lanes=(exact-baseline exact-fused39 double-baseline double-fused39)
for lane in "${lanes[@]}"; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

for lane in "${lanes[@]}"; do
  run_lane "$lane" final "$output_dir/$lane-summary.txt"
  binary="$output_dir/nl-native-${lane%%-*}"
  options=(--accept-only --count-fixed-quotients --binary-scale-bits=40)
  if [[ "$lane" == exact-* ]]; then
    binary="$output_dir/nl-native-mixed"
    options+=(--dyadic-shift-fixed-quotient)
  else
    binary="$output_dir/nl-native-double"
  fi
  if [[ "$lane" == *-fused39 ]]; then
    options+=(--fused-polynomial-max-steps=39)
  fi
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M' \
    -o "$output_dir/$lane-resource.txt" \
    "$binary" "$program" "$jobs" "$expected" "${options[@]}" \
    >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*accepted=875' \
    "$output_dir/$lane-results.txt"
done

cmp "$output_dir/exact-baseline-bounds.txt" \
  "$output_dir/exact-fused39-bounds.txt"

"$bound_analyzer" "$output_dir/double-baseline-results.txt" \
  "$output_dir/double-fused39-results.txt" \
  >"$output_dir/double-fused39-vs-baseline-bounds.json"
"$bound_analyzer" "$output_dir/exact-baseline-results.txt" \
  "$output_dir/double-baseline-results.txt" \
  >"$output_dir/double-vs-exact-baseline-bounds.json"
"$bound_analyzer" "$output_dir/exact-fused39-results.txt" \
  "$output_dir/double-fused39-results.txt" \
  >"$output_dir/double-vs-exact-fused39-bounds.json"

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
    lanes[1] = "exact-baseline"; lanes[2] = "exact-fused39";
    lanes[3] = "double-baseline"; lanes[4] = "double-fused39";
    for (j = 1; j <= 4; ++j) {
      lane = lanes[j];
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane],
        p, e, p + e, minimum_accepted[lane];
    }
    eb = evaluation_sum["exact-baseline"] / count["exact-baseline"];
    ef = evaluation_sum["exact-fused39"] / count["exact-fused39"];
    db = evaluation_sum["double-baseline"] / count["double-baseline"];
    df = evaluation_sum["double-fused39"] / count["double-fused39"];
    printf "exact_fused39_speedup\t%d\t0\t%.9f\t0\t0\n", count["exact-baseline"], eb / ef;
    printf "double_fused39_speedup\t%d\t0\t%.9f\t0\t0\n", count["double-baseline"], db / df;
    printf "baseline_exact_over_double\t%d\t0\t%.9f\t0\t0\n", count["exact-baseline"], eb / db;
    printf "fused39_exact_over_double\t%d\t0\t%.9f\t0\t0\n", count["exact-fused39"], ef / df;
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v mixed="$build_mixed_end" \
    -v double="$build_double_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_mixed\t%.9f\n", (mixed - begin) / 1000000000;
    printf "build_double\t%.9f\n", (double - mixed) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$bound_analyzer" "$program" "$jobs" \
  "$expected" "$summaries" "$output_dir"/*-results.txt \
  "$output_dir"/*-bounds.txt "$output_dir"/*-bounds.json \
  "$output_dir"/phase-times.tsv "$output_dir"/one-time-costs.tsv \
  >"$output_dir/result-files.sha256"

printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_FUSED39_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
