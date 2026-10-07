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
payload_verifier="$repo_root/scripts/verify-nl-case10173-angle-payloads.py"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
historical_specialized_seconds=0.082490265

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 -I"$boost_include" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-int128"
build_end=$(date +%s%N)

common_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --decimal-scale=10000000
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
)

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local lane=$1
  local repetition=$2
  local option=--computed-tight-sqrt-certificates
  if [[ "$lane" == precomputed ]]; then
    option=--precompute-tight-sqrt-certificates
  fi
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${common_options[@]}" "$option" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

run_lane computed warmup
run_lane precomputed warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane computed "$repetition"
    run_lane precomputed "$repetition"
  else
    run_lane precomputed "$repetition"
    run_lane computed "$repetition"
  fi
done

for lane in computed precomputed; do
  option=--computed-tight-sqrt-certificates
  if [[ "$lane" == precomputed ]]; then
    option=--precompute-tight-sqrt-certificates
  fi
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${common_options[@]}" "$option" >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
  rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
done
cmp "$output_dir/computed-bounds.txt" \
  "$output_dir/precomputed-bounds.txt"

awk -v historical="$historical_specialized_seconds" '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = 0; evaluation = 0; accepted = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    count[lane] += 1;
    if (count[lane] == 1 || accepted < minimum_accepted[lane]) {
      minimum_accepted[lane] = accepted;
    }
  }
  END {
    cp = preparation_sum["computed"] / count["computed"];
    ce = evaluation_sum["computed"] / count["computed"];
    pp = preparation_sum["precomputed"] / count["precomputed"];
    pe = evaluation_sum["precomputed"] / count["precomputed"];
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    printf "computed_during_evaluation\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["computed"], cp, ce, cp + ce, minimum_accepted["computed"];
    printf "precomputed_then_validated\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["precomputed"], pp, pe, pp + pe, minimum_accepted["precomputed"];
    printf "recurring_evaluation_speedup\t%d\t0\t%.9f\t0\t%d\n", count["precomputed"], ce / pe, minimum_accepted["precomputed"];
    printf "single_batch_speedup\t%d\t0\t0\t%.9f\t%d\n", count["precomputed"], (cp + ce) / (pp + pe), minimum_accepted["precomputed"];
    printf "precomputed_over_historical_specialized_evaluation\t%d\t0\t%.9f\t0\t%d\n", count["precomputed"], pe / historical, minimum_accepted["precomputed"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$source_file" "$payload_verifier" "$program" "$jobs" \
  "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$summaries" \
  "$output_dir/computed-results.txt" \
  "$output_dir/precomputed-results.txt" \
  "$output_dir/computed-bounds.txt" \
  "$output_dir/precomputed-bounds.txt" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_FULL4173_SQRT_PREPARATION_PAIRED_OK DEVELOPMENT_NON_RELEASE'
