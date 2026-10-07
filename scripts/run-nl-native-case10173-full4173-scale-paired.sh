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
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
  --computed-tight-sqrt-certificates
)

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local scale=$1
  local repetition=$2
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${common_options[@]}" --decimal-scale="$scale" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ scale_lane=$scale repetition=$repetition/" >>"$summaries"
}

run_lane 10000000 warmup
run_lane 10000000000 warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane 10000000 "$repetition"
    run_lane 10000000000 "$repetition"
  else
    run_lane 10000000000 "$repetition"
    run_lane 10000000 "$repetition"
  fi
done

for scale in 10000000 10000000000; do
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${common_options[@]}" --decimal-scale="$scale" \
    >"$output_dir/scale-$scale-results.txt"
  rg -q 'cells=4173 .*accepted=4173' \
    "$output_dir/scale-$scale-results.txt"
done

set +e
"$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
  "${common_options[@]}" --decimal-scale=1000000 \
  >"$output_dir/scale-1000000-rejected.txt" \
  2>"$output_dir/scale-1000000-rejected.stderr"
rejected_status=$?
set -e
printf '%s\n' "$rejected_status" \
  >"$output_dir/scale-1000000-rejected.exit-status"
[[ "$rejected_status" -eq 1 ]]
rg -q 'accepted=4149' "$output_dir/scale-1000000-rejected.txt"

awk -v historical="$historical_specialized_seconds" '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = 0; evaluation = 0; accepted = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "scale_lane") lane = field[2];
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
    lp = preparation_sum["10000000"] / count["10000000"];
    le = evaluation_sum["10000000"] / count["10000000"];
    hp = preparation_sum["10000000000"] / count["10000000000"];
    he = evaluation_sum["10000000000"] / count["10000000000"];
    print "scale\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    printf "1e7\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["10000000"], lp, le, lp + le, minimum_accepted["10000000"];
    printf "1e10\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["10000000000"], hp, he, hp + he, minimum_accepted["10000000000"];
    printf "1e10_over_1e7_evaluation\t%d\t0\t%.9f\t0\t%d\n", count["10000000"], he / le, minimum_accepted["10000000"];
    printf "1e10_over_1e7_batch\t%d\t0\t0\t%.9f\t%d\n", count["10000000"], (hp + he) / (lp + le), minimum_accepted["10000000"];
    printf "1e7_over_historical_specialized_evaluation\t%d\t0\t%.9f\t0\t%d\n", count["10000000"], le / historical, minimum_accepted["10000000"];
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
  "$output_dir/scale-10000000-results.txt" \
  "$output_dir/scale-10000000000-results.txt" \
  "$output_dir/scale-1000000-rejected.txt" \
  "$output_dir/scale-1000000-rejected.stderr" \
  "$output_dir/scale-1000000-rejected.exit-status" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_FULL4173_SCALE_PAIRED_OK DEVELOPMENT_NON_RELEASE'
