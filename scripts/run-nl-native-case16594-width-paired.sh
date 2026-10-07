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
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  "${common_defines[@]}" "$source_file" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-mpz"
build_mpz_end=$(date +%s%N)
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
  case "$lane" in
    mpz) binary="$output_dir/nl-native-mpz" ;;
    checked-int256) binary="$output_dir/nl-native-checked256" ;;
    padded-double) binary="$output_dir/nl-native-double" ;;
    *) printf 'unknown lane: %s\n' "$lane" >&2; exit 2 ;;
  esac
  "$binary" "$program" "$jobs" "$expected" \
    --accept-only --count-fixed-quotients |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(mpz checked-int256 padded-double)
for lane in "${lanes[@]}"; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

"$output_dir/nl-native-mpz" "$program" "$jobs" "$expected" \
  --count-fixed-quotients >"$output_dir/mpz-results.txt"
"$output_dir/nl-native-checked256" "$program" "$jobs" "$expected" \
  --count-fixed-quotients >"$output_dir/checked256-results.txt"
"$output_dir/nl-native-double" "$program" "$jobs" "$expected" \
  --accept-only --count-fixed-quotients >"$output_dir/padded-double-results.txt"

rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=mpz .*case_id=16594 .*matched=875 .*accepted=875' \
  "$output_dir/mpz-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=checked-int256 .*case_id=16594 .*matched=875 .*accepted=875' \
  "$output_dir/checked256-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=double-integer .*case_id=16594 .*accepted=875' \
  "$output_dir/padded-double-results.txt"

"$bound_analyzer" "$output_dir/mpz-results.txt" \
  "$output_dir/checked256-results.txt" \
  >"$output_dir/checked256-vs-mpz-bounds.json"
"$bound_analyzer" "$output_dir/mpz-results.txt" \
  "$output_dir/padded-double-results.txt" \
  >"$output_dir/padded-double-vs-mpz-bounds.json"

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
    lanes[1] = "mpz"; lanes[2] = "checked-int256"; lanes[3] = "padded-double";
    for (j = 1; j <= 3; ++j) {
      lane = lanes[j];
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane], p, e, p + e, minimum_accepted[lane];
    }
    mpz = evaluation_sum["mpz"] / count["mpz"];
    checked = evaluation_sum["checked-int256"] / count["checked-int256"];
    hardware = evaluation_sum["padded-double"] / count["padded-double"];
    printf "mpz_over_checked256_evaluation\t%d\t0\t%.9f\t0\t0\n", count["mpz"], mpz / checked;
    printf "checked256_over_padded_double_evaluation\t%d\t0\t%.9f\t0\t0\n", count["mpz"], checked / hardware;
    printf "mpz_over_padded_double_evaluation\t%d\t0\t%.9f\t0\t0\n", count["mpz"], mpz / hardware;
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v mpz="$build_mpz_end" \
    -v checked="$build_checked256_end" -v double="$build_double_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_mpz\t%.9f\n", (mpz - begin) / 1000000000;
    printf "build_checked256\t%.9f\n", (checked - mpz) / 1000000000;
    printf "build_double\t%.9f\n", (double - checked) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$bound_analyzer" "$program" "$jobs" \
  "$expected" "$output_dir/summaries.txt" \
  "$output_dir/mpz-results.txt" "$output_dir/checked256-results.txt" \
  "$output_dir/padded-double-results.txt" \
  "$output_dir/checked256-vs-mpz-bounds.json" \
  "$output_dir/padded-double-vs-mpz-bounds.json" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_WIDTH_PAIRED_OK DEVELOPMENT_NON_RELEASE'
