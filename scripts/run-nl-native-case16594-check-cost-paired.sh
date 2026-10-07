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
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-checked"
build_checked_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_MIXED_INT128_192_UNCHECKED=1 \
  "${defines[@]}" "$source_file" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-unchecked"
build_unchecked_end=$(date +%s%N)

summaries="$output_dir/summaries.txt"
: >"$summaries"

run_lane() {
  local lane=$1 repetition=$2 destination=$3 binary
  case "$lane" in
    checked) binary="$output_dir/nl-native-checked" ;;
    unchecked) binary="$output_dir/nl-native-unchecked" ;;
    *) printf 'unknown lane: %s\n' "$lane" >&2; exit 2 ;;
  esac
  "$binary" "$program" "$jobs" "$expected" --accept-only \
    --count-fixed-quotients --binary-scale-bits=40 \
    --dyadic-shift-fixed-quotient |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(checked unchecked)
for lane in "${lanes[@]}"; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    order=(checked unchecked)
  else
    order=(unchecked checked)
  fi
  for lane in "${order[@]}"; do
    run_lane "$lane" "$repetition" "$summaries"
  done
done

for lane in "${lanes[@]}"; do
  run_lane "$lane" final "$output_dir/$lane-summary.txt"
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M' \
    -o "$output_dir/$lane-resource.txt" \
    "$output_dir/nl-native-$lane" "$program" "$jobs" "$expected" \
    --accept-only --count-fixed-quotients --binary-scale-bits=40 \
    --dyadic-shift-fixed-quotient >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*accepted=875' \
    "$output_dir/$lane-results.txt"
done

cmp "$output_dir/checked-bounds.txt" "$output_dir/unchecked-bounds.txt"

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
    lanes[1] = "checked"; lanes[2] = "unchecked";
    for (j = 1; j <= 2; ++j) {
      lane = lanes[j];
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane],
        p, e, p + e, minimum_accepted[lane];
    }
    checked = evaluation_sum["checked"] / count["checked"];
    unchecked = evaluation_sum["unchecked"] / count["unchecked"];
    checked_batch = checked + preparation_sum["checked"] / count["checked"];
    unchecked_batch = unchecked + preparation_sum["unchecked"] / count["unchecked"];
    printf "checked_over_unchecked_evaluation\t%d\t0\t%.9f\t0\t0\n", count["checked"], checked / unchecked;
    printf "checked_over_unchecked_batch\t%d\t0\t0\t%.9f\t0\n", count["checked"], checked_batch / unchecked_batch;
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v checked="$build_checked_end" \
    -v unchecked="$build_unchecked_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_checked\t%.9f\n", (checked - begin) / 1000000000;
    printf "build_unchecked\t%.9f\n", (unchecked - checked) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$summaries" "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir"/phase-times.tsv "$output_dir"/one-time-costs.tsv \
  >"$output_dir/result-files.sha256"

printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_CHECK_COST_PAIRED_OK DEVELOPMENT_NON_RELEASE'
