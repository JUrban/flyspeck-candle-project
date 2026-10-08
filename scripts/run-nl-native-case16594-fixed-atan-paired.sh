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
analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$jobs" "$expected" "$source_file"; do
  [[ -f "$input" ]]
done
[[ -x "$analyzer" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_FIXED_INT128=1 \
  -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 \
  -DCANDLE_NL_CASE_ID=16594 -DCANDLE_NL_SQRT_SLOTS=10 \
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-builtin"
build_end=$(date +%s%N)

common_options=(
  --accept-only
  --count-fixed-quotients
  --binary-scale-bits=40
  --dyadic-shift-fixed-quotient
  --sign-specialized-interval-products
  --specialized-delta-radicands
  --specialized-delta-derivatives
  --fixed-sqrt-inverse-kernels
)

run_lane() {
  local lane=$1 repetition=$2 destination=$3
  local -a options=("${common_options[@]}")
  if [[ "$lane" == fixed-atan ]]; then
    options+=(--fixed-atan-kernel)
  fi
  "$output_dir/nl-native-builtin" "$program" "$jobs" "$expected" \
    "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(rational-atan fixed-atan)
for lane in "${lanes[@]}"; do
  run_lane "$lane" warmup /dev/null
done
summaries="$output_dir/summaries.txt"
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane rational-atan "$repetition" "$summaries"
    run_lane fixed-atan "$repetition" "$summaries"
  else
    run_lane fixed-atan "$repetition" "$summaries"
    run_lane rational-atan "$repetition" "$summaries"
  fi
done

for lane in "${lanes[@]}"; do
  options=("${common_options[@]}")
  if [[ "$lane" == fixed-atan ]]; then
    options+=(--fixed-atan-kernel)
  fi
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-resource.txt" \
    "$output_dir/nl-native-builtin" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-summary.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*fixed_sqrt_inverse_kernels=1 .*accepted=875' \
    "$output_dir/$lane-summary.txt"
done
rg -q ' fixed_atan_kernel=0 ' "$output_dir/rational-atan-summary.txt"
rg -q ' fixed_atan_kernel=1 ' "$output_dir/fixed-atan-summary.txt"

"$analyzer" "$output_dir/rational-atan-results.txt" \
  "$output_dir/fixed-atan-results.txt" \
  >"$output_dir/fixed-vs-rational-bounds.json"

# The fixed range-reduced kernel is only a candidate until every resulting
# Taylor enclosure has been checked to contain the rational reference.
"$output_dir/nl-native-builtin" "$program" "$jobs" "$expected" \
  "${common_options[@]}" --fixed-atan-kernel \
  --verify-fixed-kernel-enclosures \
  >"$output_dir/fixed-atan-crosscheck-results.txt"
rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
  "$output_dir/fixed-atan-crosscheck-results.txt" \
  >"$output_dir/fixed-atan-crosscheck-summary.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*fixed_atan_kernel=1 verify_fixed_kernel_enclosures=1 .*accepted=875' \
  "$output_dir/fixed-atan-crosscheck-summary.txt"

"$output_dir/nl-native-builtin" "$program" "$jobs" "$expected" \
  "${common_options[@]}" --profile \
  >"$output_dir/rational-atan-instruction-profile.txt"
[[ $(rg -c '^CANDLE_NL_NATIVE_FIXED_SCALE_PROFILE ' \
  "$output_dir/rational-atan-instruction-profile.txt") -eq 167 ]]
awk '
  /^CANDLE_NL_NATIVE_FIXED_SCALE_PROFILE / {
    label = ""; nanoseconds = products = completions = 0
    for (i = 1; i <= NF; ++i) {
      split($i, field, "=")
      if (field[1] == "label") label = field[2]
      if (field[1] == "nanoseconds") nanoseconds = field[2] + 0
      if (field[1] == "interval_products") products = field[2] + 0
      if (field[1] == "completed_results") completions = field[2] + 0
    }
    kind = label; sub(/:.*/, "", kind)
    count[kind]++
    time[kind] += nanoseconds
    interval_products[kind] += products
    completed_results[kind] += completions
    total += nanoseconds
  }
  END {
    print "kind\tinstructions\tseconds\tpercent\tinterval_products\tcompleted_results"
    for (kind in time) {
      printf "%s\t%d\t%.9f\t%.6f\t%d\t%d\n", kind, count[kind], time[kind] / 1000000000, 100 * time[kind] / total, interval_products[kind], completed_results[kind]
    }
    printf "profile_total\t167\t%.9f\t100.000000\t0\t0\n", total / 1000000000
  }
' "$output_dir/rational-atan-instruction-profile.txt" |
  {
    IFS= read -r header
    printf '%s\n' "$header"
    sort -t $'\t' -k3,3nr
  } >"$output_dir/stage-profile.tsv"

awk '
  function value(name, i, field) {
    for (i = 1; i <= NF; ++i) {
      split($i, field, "=")
      if (field[1] == name) return field[2]
    }
  }
  {
    lane = value("lane"); if (lane == "") next
    count[lane]++
    preparation[lane] += value("preparation_seconds")
    evaluation[lane] += value("evaluation_seconds")
    accepted = value("accepted") + 0
    if (!(lane in minimum) || accepted < minimum[lane]) minimum[lane] = accepted
  }
  END {
    print "lane\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted"
    names[1] = "rational-atan"; names[2] = "fixed-atan"
    for (i = 1; i <= 2; ++i) {
      lane = names[i]
      p = preparation[lane] / count[lane]
      e = evaluation[lane] / count[lane]
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane], p, e, p + e, minimum[lane]
    }
    rational_e = evaluation["rational-atan"] / count["rational-atan"]
    fixed_e = evaluation["fixed-atan"] / count["fixed-atan"]
    rational_p = preparation["rational-atan"] / count["rational-atan"]
    fixed_p = preparation["fixed-atan"] / count["fixed-atan"]
    printf "fixed_atan_evaluation_speedup\t%d\t0\t%.9f\t0\t875\n", count["fixed-atan"], rational_e / fixed_e
    printf "fixed_atan_batch_speedup\t%d\t0\t0\t%.9f\t875\n", count["fixed-atan"], (rational_p + rational_e) / (fixed_p + fixed_e)
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v end="$build_end" 'BEGIN {
  print "metric\tseconds"
  printf "build_seconds\t%.9f\n", (end - begin) / 1000000000
}' >"$output_dir/one-time-costs.tsv"

{
  echo 'status=DEVELOPMENT_NON_RELEASE'
  echo 'held_constant=authenticated_expression_graph,boxes,fixed_scale,endpoint_representation,generic_jet_propagation'
  echo 'changed_axis=rational_atan_value_and_derivatives_vs_fixed_range_reduced_atan_value_and_derivatives'
  echo 'rational_enclosure_crosscheck=passed_875/875'
  echo 'accepted_rational=875/875'
  echo 'accepted_fixed=875/875'
} >"$output_dir/decision.txt"

sha256sum "$0" "$source_file" "$analyzer" "$program" "$jobs" \
  "$expected" "$output_dir/nl-native-builtin" "$summaries" \
  "$output_dir"/*-results.txt "$output_dir"/*-summary.txt \
  "$output_dir"/*-bounds.txt \
  "$output_dir/fixed-vs-rational-bounds.json" \
  "$output_dir/rational-atan-instruction-profile.txt" \
  "$output_dir/stage-profile.tsv" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  "$output_dir/decision.txt" >"$output_dir/result-files.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_FIXED_ATAN_PAIRED_OK DEVELOPMENT_NON_RELEASE'
