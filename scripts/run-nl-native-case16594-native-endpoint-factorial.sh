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
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$jobs" "$expected" "$source_file"; do
  [[ -f "$input" ]]
done
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

common=(-std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include")
defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)

build_begin=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_MIXED_INT128_192=1 "${defines[@]}" \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-boost"
build_boost_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_INT128=1 \
  -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 "${defines[@]}" \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-builtin"
build_builtin_end=$(date +%s%N)

options=(
  --accept-only
  --count-fixed-quotients
  --binary-scale-bits=40
  --dyadic-shift-fixed-quotient
  --specialized-delta-radicands
  --specialized-delta-derivatives
  --sign-specialized-interval-products
)

run_lane() {
  local lane=$1 repetition=$2 destination=$3
  "$output_dir/nl-native-$lane" "$program" "$jobs" "$expected" \
    "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
lanes=(boost builtin)
for lane in "${lanes[@]}"; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    order=(boost builtin)
  else
    order=(builtin boost)
  fi
  for lane in "${order[@]}"; do
    run_lane "$lane" "$repetition" "$summaries"
  done
done

for lane in "${lanes[@]}"; do
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M' \
    -o "$output_dir/$lane-resource.txt" \
    "$output_dir/nl-native-$lane" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
done

rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=mixed-checked-int128-192 .*mixed_wide_taylor_completions=162750 mixed_wide_narrowings=325500 .*accepted=875' \
  "$output_dir/boost-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=mixed-native-int128-checked-int192 .*mixed_wide_taylor_completions=162750 mixed_wide_narrowings=325500 .*accepted=875' \
  "$output_dir/builtin-results.txt"
cmp "$output_dir/boost-bounds.txt" "$output_dir/builtin-bounds.txt"

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
    if (count[lane] == 1 || accepted < minimum[lane]) minimum[lane] = accepted;
  }
  END {
    print "lane\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    names[1] = "boost"; names[2] = "builtin";
    for (i = 1; i <= 2; ++i) {
      lane = names[i];
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane],
        p, e, p + e, minimum[lane];
    }
    bp = preparation_sum["boost"] / count["boost"];
    be = evaluation_sum["boost"] / count["boost"];
    np = preparation_sum["builtin"] / count["builtin"];
    ne = evaluation_sum["builtin"] / count["builtin"];
    printf "boost_over_builtin_evaluation\t%d\t0\t%.9f\t0\t875\n", count["boost"], be / ne;
    printf "boost_over_builtin_batch\t%d\t0\t0\t%.9f\t875\n", count["boost"], (bp + be) / (np + ne);
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v boost="$build_boost_end" \
    -v builtin="$build_builtin_end" 'BEGIN {
  print "phase\tseconds";
  printf "build_boost_mixed\t%.9f\n", (boost - begin) / 1000000000;
  printf "build_builtin_endpoint\t%.9f\n", (builtin - boost) / 1000000000;
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/summaries.txt" "$output_dir"/*-results.txt \
  "$output_dir"/*-bounds.txt "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/result-files.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_NATIVE_ENDPOINT_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
