#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
output_dir=$3
repetitions=$4
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
bound_analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$source_file" ]]
[[ -x "$bound_analyzer" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

common_defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  "${common_defines[@]}" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-mpz"
build_exact_end=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_DOUBLE=1 "${common_defines[@]}" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-double"
build_double_end=$(date +%s%N)

awk 'BEGIN { for (i = 0; i < 875; ++i) print i "\t0" }' \
  >"$output_dir/zero-expected.tsv"

"$output_dir/nl-native-mpz" "$program" "$jobs" \
  "$output_dir/zero-expected.tsv" --accept-only \
  >"$output_dir/exact-reference-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*case_id=16594 .*accepted=875' \
  "$output_dir/exact-reference-results.txt"
awk '
  /^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT / {
    idx = upper = "";
    for (i = 1; i <= NF; ++i) {
      split($i, field, "=");
      if (field[1] == "index") idx = field[2];
      if (field[1] == "upper") upper = field[2];
    }
    if (idx == "" || upper == "" || idx != count) exit 1;
    print idx "\t" upper;
    count++;
  }
  END { if (count != 875) exit 1 }
' "$output_dir/exact-reference-results.txt" \
  >"$output_dir/exact-expected.tsv"

common_options=(--count-fixed-quotients)
summaries="$output_dir/summaries.txt"
: >"$summaries"

run_lane() {
  local lane=$1 repetition=$2 destination=$3 binary
  case "$lane" in
    mpz) binary="$output_dir/nl-native-mpz" ;;
    padded-double) binary="$output_dir/nl-native-double" ;;
    *) printf 'unknown lane: %s\n' "$lane" >&2; exit 2 ;;
  esac
  "$binary" "$program" "$jobs" "$output_dir/exact-expected.tsv" \
    --accept-only "${common_options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(mpz padded-double)
for lane in "${lanes[@]}"; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

"$output_dir/nl-native-mpz" "$program" "$jobs" \
  "$output_dir/exact-expected.tsv" "${common_options[@]}" \
  >"$output_dir/exact-results.txt"
"$output_dir/nl-native-double" "$program" "$jobs" \
  "$output_dir/exact-expected.tsv" --accept-only "${common_options[@]}" \
  >"$output_dir/padded-double-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*case_id=16594 .*matched=875 .*accepted=875' \
  "$output_dir/exact-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*case_id=16594 .*accepted=875' \
  "$output_dir/padded-double-results.txt"

"$bound_analyzer" "$output_dir/exact-results.txt" \
  "$output_dir/padded-double-results.txt" \
  >"$output_dir/padded-double-vs-exact-bounds.json"

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
    lanes[1] = "mpz"; lanes[2] = "padded-double";
    for (j = 1; j <= 2; ++j) {
      lane = lanes[j];
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane], p, e, p + e, minimum_accepted[lane];
    }
    exact = evaluation_sum["mpz"] / count["mpz"];
    hardware = evaluation_sum["padded-double"] / count["padded-double"];
    printf "mpz_over_padded_double_evaluation\t%d\t0\t%.9f\t0\t0\n", count["mpz"], exact / hardware;
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v exact="$build_exact_end" \
    -v double="$build_double_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_exact\t%.9f\n", (exact - begin) / 1000000000;
    printf "build_double\t%.9f\n", (double - exact) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$bound_analyzer" "$program" "$jobs" \
  "$output_dir/exact-expected.tsv" "$output_dir/summaries.txt" \
  "$output_dir/exact-results.txt" \
  "$output_dir/padded-double-results.txt" \
  "$output_dir/padded-double-vs-exact-bounds.json" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_REPRESENTATION_PAIRED_OK DEVELOPMENT_NON_RELEASE'
