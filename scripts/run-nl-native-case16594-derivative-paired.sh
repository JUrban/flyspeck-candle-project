#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv EXACT-EXPECTED.tsv OUTPUT-DIR REPETITIONS\n' "$0" >&2
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

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$bound_analyzer" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_DOUBLE=1 \
  -DCANDLE_NL_CASE_ID=16594 \
  -DCANDLE_NL_SQRT_SLOTS=10 \
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-double"
build_end=$(date +%s%N)

summaries="$output_dir/summaries.txt"
: >"$summaries"

run_lane() {
  local lane=$1 repetition=$2 destination=$3
  local options=(--accept-only --count-fixed-quotients)
  if [[ "$lane" == compact ]]; then
    options+=(--compact-support-jets)
  elif [[ "$lane" != dense ]]; then
    printf 'unknown lane: %s\n' "$lane" >&2
    exit 2
  fi
  "$output_dir/nl-native-double" "$program" "$jobs" "$expected" \
    "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(dense compact)
for lane in "${lanes[@]}"; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

"$output_dir/nl-native-double" "$program" "$jobs" "$expected" \
  --accept-only --count-fixed-quotients >"$output_dir/dense-results.txt"
"$output_dir/nl-native-double" "$program" "$jobs" "$expected" \
  --accept-only --count-fixed-quotients --compact-support-jets \
  >"$output_dir/compact-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*case_id=16594 .*accepted=875' \
  "$output_dir/dense-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*case_id=16594 .*accepted=875' \
  "$output_dir/compact-results.txt"

"$bound_analyzer" "$output_dir/dense-results.txt" \
  "$output_dir/compact-results.txt" \
  >"$output_dir/compact-vs-dense-bounds.json"

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
    lanes[1] = "dense"; lanes[2] = "compact";
    for (j = 1; j <= 2; ++j) {
      lane = lanes[j];
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane], p, e, p + e, minimum_accepted[lane];
    }
    dense = evaluation_sum["dense"] / count["dense"];
    compact = evaluation_sum["compact"] / count["compact"];
    printf "dense_over_compact_evaluation\t%d\t0\t%.9f\t0\t0\n", count["dense"], dense / compact;
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v finish="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_double\t%.9f\n", (finish - begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$bound_analyzer" "$program" "$jobs" \
  "$expected" "$output_dir/summaries.txt" \
  "$output_dir/dense-results.txt" "$output_dir/compact-results.txt" \
  "$output_dir/compact-vs-dense-bounds.json" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_DERIVATIVE_PAIRED_OK DEVELOPMENT_NON_RELEASE'
