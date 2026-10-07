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
  --precompute-tight-sqrt-certificates
)

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local lane=$1
  local repetition=$2
  local options=("${common_options[@]}")
  if [[ "$lane" == hardware-seeded ]]; then
    options+=(--hardware-seeded-integer-sqrt)
  fi
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

run_lane binary-search warmup
run_lane hardware-seeded warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane binary-search "$repetition"
    run_lane hardware-seeded "$repetition"
  else
    run_lane hardware-seeded "$repetition"
    run_lane binary-search "$repetition"
  fi
done

for lane in binary-search hardware-seeded; do
  options=("${common_options[@]}")
  if [[ "$lane" == hardware-seeded ]]; then
    options+=(--hardware-seeded-integer-sqrt)
  fi
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
  rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
done
cmp "$output_dir/binary-search-bounds.txt" \
  "$output_dir/hardware-seeded-bounds.txt"

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
    bp = preparation_sum["binary-search"] / count["binary-search"];
    be = evaluation_sum["binary-search"] / count["binary-search"];
    hp = preparation_sum["hardware-seeded"] / count["hardware-seeded"];
    he = evaluation_sum["hardware-seeded"] / count["hardware-seeded"];
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    printf "binary_search_then_validated\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["binary-search"], bp, be, bp + be, minimum_accepted["binary-search"];
    printf "hardware_seeded_then_corrected_and_validated\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["hardware-seeded"], hp, he, hp + he, minimum_accepted["hardware-seeded"];
    printf "preparation_speedup\t%d\t%.9f\t0\t0\t%d\n", count["hardware-seeded"], bp / hp, minimum_accepted["hardware-seeded"];
    printf "single_batch_speedup\t%d\t0\t0\t%.9f\t%d\n", count["hardware-seeded"], (bp + be) / (hp + he), minimum_accepted["hardware-seeded"];
    printf "seeded_batch_over_historical_specialized\t%d\t0\t0\t%.9f\t%d\n", count["hardware-seeded"], (hp + he) / historical, minimum_accepted["hardware-seeded"];
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
  "$output_dir/binary-search-results.txt" \
  "$output_dir/hardware-seeded-results.txt" \
  "$output_dir/binary-search-bounds.txt" \
  "$output_dir/hardware-seeded-bounds.txt" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_FULL4173_SQRT_SEED_PAIRED_OK DEVELOPMENT_NON_RELEASE'
