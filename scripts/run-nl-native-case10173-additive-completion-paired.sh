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
historical_specialized_seconds=0.082490265

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 "$source_file" \
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
  --precompute-tight-sqrt-certificates
  --count-fixed-quotients
  --binary-scale-bits=23
  --dyadic-shift-fixed-quotient
  --fuse-consecutive-adds
)

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local lane=$1
  local repetition=$2
  local options=("${common_options[@]}")
  if [[ "$lane" == deferred-leaves ]]; then
    options+=(--defer-additive-leaf-completion)
  elif [[ "$lane" != completed-leaves ]]; then
    printf 'unknown lane: %s\n' "$lane" >&2
    exit 2
  fi
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

lanes=(completed-leaves deferred-leaves)
for lane in "${lanes[@]}"; do
  run_lane "$lane" warmup
done
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition"
  done
done

: >"$output_dir/peak-rss-kb.tsv"
printf 'lane\tpeak_rss_kb\n' >>"$output_dir/peak-rss-kb.tsv"
for lane in "${lanes[@]}"; do
  options=("${common_options[@]}")
  if [[ "$lane" == deferred-leaves ]]; then
    options+=(--defer-additive-leaf-completion)
  fi
  /usr/bin/time -f '%M' -o "$output_dir/$lane-peak-rss-kb.txt" \
    "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
  printf '%s\t%s\n' "$lane" \
    "$(cat "$output_dir/$lane-peak-rss-kb.txt")" \
    >>"$output_dir/peak-rss-kb.tsv"
done
cmp "$output_dir/completed-leaves-bounds.txt" \
  "$output_dir/deferred-leaves-bounds.txt"

awk -v historical="$historical_specialized_seconds" '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = 0; evaluation = 0; accepted = 0;
    quotients = 0; completed = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "evaluation_dyadic_shift_quotients") quotients = field[2] + 0;
      if (field[1] == "completed_results") completed = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    quotient_sum[lane] += quotients;
    completed_sum[lane] += completed;
    count[lane] += 1;
    if (count[lane] == 1 || accepted < minimum_accepted[lane]) {
      minimum_accepted[lane] = accepted;
    }
  }
  END {
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tmean_shift_quotients\tmean_completed_results\tminimum_accepted";
    for (lane_index = 1; lane_index <= 2; ++lane_index) {
      lane = lane_index == 1 ? "completed-leaves" : "deferred-leaves";
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.0f\t%.0f\t%d\n", lane, count[lane], p, e, p + e, quotient_sum[lane] / count[lane], completed_sum[lane] / count[lane], minimum_accepted[lane];
    }
    ce = evaluation_sum["completed-leaves"] / count["completed-leaves"];
    de = evaluation_sum["deferred-leaves"] / count["deferred-leaves"];
    cp = preparation_sum["completed-leaves"] / count["completed-leaves"];
    dp = preparation_sum["deferred-leaves"] / count["deferred-leaves"];
    printf "deferred_evaluation_speedup\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["deferred-leaves"], ce / de, minimum_accepted["deferred-leaves"];
    printf "deferred_batch_speedup\t%d\t0\t0\t%.9f\t0\t0\t%d\n", count["deferred-leaves"], (cp + ce) / (dp + de), minimum_accepted["deferred-leaves"];
    printf "deferred_over_cpp_specialized\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["deferred-leaves"], de / historical, minimum_accepted["deferred-leaves"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_int128\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$source_file" "$payload_verifier" "$program" "$jobs" \
  "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$summaries" \
  "$output_dir/completed-leaves-results.txt" \
  "$output_dir/deferred-leaves-results.txt" \
  "$output_dir/completed-leaves-bounds.txt" \
  "$output_dir/deferred-leaves-bounds.txt" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  "$output_dir/peak-rss-kb.tsv" >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_ADDITIVE_COMPLETION_PAIRED_OK DEVELOPMENT_NON_RELEASE'
