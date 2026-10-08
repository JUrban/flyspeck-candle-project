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

certificates="$output_dir/reciprocal-certificates.tsv"
"$output_dir/nl-native-builtin" "$program" "$jobs" "$expected" \
  "${common_options[@]}" \
  --capture-reciprocal-certificates="$certificates" \
  >"$output_dir/capture-results.txt"
rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
  "$output_dir/capture-results.txt" >"$output_dir/capture-summary.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*fixed_sqrt_inverse_kernels=1 .*reciprocal_certificate_mode=capture reciprocal_certificate_records=50750 .*accepted=875' \
  "$output_dir/capture-summary.txt"
[[ $(wc -l <"$certificates") -eq 50750 ]]

run_lane() {
  local lane=$1 repetition=$2 destination=$3
  local -a options=("${common_options[@]}")
  if [[ "$lane" == supplied ]]; then
    options+=(--use-reciprocal-certificates="$certificates")
  fi
  "$output_dir/nl-native-builtin" "$program" "$jobs" "$expected" \
    "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(computed supplied)
for lane in "${lanes[@]}"; do
  run_lane "$lane" warmup /dev/null
done
summaries="$output_dir/summaries.txt"
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane computed "$repetition" "$summaries"
    run_lane supplied "$repetition" "$summaries"
  else
    run_lane supplied "$repetition" "$summaries"
    run_lane computed "$repetition" "$summaries"
  fi
done

for lane in "${lanes[@]}"; do
  options=("${common_options[@]}")
  if [[ "$lane" == supplied ]]; then
    options+=(--use-reciprocal-certificates="$certificates")
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
rg -q ' reciprocal_certificate_mode=none reciprocal_certificate_records=0 ' \
  "$output_dir/computed-summary.txt"
rg -q ' reciprocal_certificate_mode=use reciprocal_certificate_records=50750 ' \
  "$output_dir/supplied-summary.txt"
cmp "$output_dir/computed-bounds.txt" "$output_dir/supplied-bounds.txt"

# The supplied stream is positional and self-checking.  A reordered input or
# malformed output must fail before it can influence an accepted result.
awk 'NR == 1 { first = $0; next }
     NR == 2 { print; print first; next }
     { print }' "$certificates" >"$output_dir/reordered-certificates.tsv"
awk -F '\t' 'BEGIN { OFS = "\t" }
     NR == 1 { temporary = $5; $5 = $6; $6 = temporary }
     { print }' "$certificates" >"$output_dir/invalid-certificates.tsv"
awk -F '\t' 'BEGIN { OFS = "\t" }
     NR == 1 {
       $5 = "170141183460469231731687303715884105727"
       $6 = "170141183460469231731687303715884105727"
     }
     { print }' "$certificates" >"$output_dir/overflow-certificates.tsv"

set +e
"$output_dir/nl-native-builtin" "$program" "$jobs" "$expected" \
  "${common_options[@]}" \
  --use-reciprocal-certificates="$output_dir/reordered-certificates.tsv" \
  >"$output_dir/reordered-stdout.txt" \
  2>"$output_dir/reordered-stderr.txt"
reordered_exit=$?
"$output_dir/nl-native-builtin" "$program" "$jobs" "$expected" \
  "${common_options[@]}" \
  --use-reciprocal-certificates="$output_dir/invalid-certificates.tsv" \
  >"$output_dir/invalid-stdout.txt" \
  2>"$output_dir/invalid-stderr.txt"
invalid_exit=$?
"$output_dir/nl-native-builtin" "$program" "$jobs" "$expected" \
  "${common_options[@]}" \
  --use-reciprocal-certificates="$output_dir/overflow-certificates.tsv" \
  >"$output_dir/overflow-stdout.txt" \
  2>"$output_dir/overflow-stderr.txt"
overflow_exit=$?
set -e
[[ "$reordered_exit" -ne 0 && "$invalid_exit" -ne 0 && \
   "$overflow_exit" -ne 0 ]]
rg -q 'reciprocal certificate input/order drift' \
  "$output_dir/reordered-stderr.txt"
rg -q 'invalid supplied reciprocal certificate' \
  "$output_dir/invalid-stderr.txt"
rg -q 'invalid supplied reciprocal certificate' \
  "$output_dir/overflow-stderr.txt"

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
    names[1] = "computed"; names[2] = "supplied"
    for (i = 1; i <= 2; ++i) {
      lane = names[i]
      p = preparation[lane] / count[lane]
      e = evaluation[lane] / count[lane]
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane], p, e, p + e, minimum[lane]
    }
    computed_e = evaluation["computed"] / count["computed"]
    supplied_e = evaluation["supplied"] / count["supplied"]
    computed_p = preparation["computed"] / count["computed"]
    supplied_p = preparation["supplied"] / count["supplied"]
    printf "supplied_evaluation_speedup\t%d\t0\t%.9f\t0\t875\n", count["supplied"], computed_e / supplied_e
    printf "supplied_batch_speedup\t%d\t0\t0\t%.9f\t875\n", count["supplied"], (computed_p + computed_e) / (supplied_p + supplied_e)
  }
' "$summaries" >"$output_dir/phase-times.tsv"

capture_preparation=$(sed -n 's/.* preparation_seconds=\([^ ]*\).*/\1/p' \
  "$output_dir/capture-summary.txt")
capture_evaluation=$(sed -n 's/.* evaluation_seconds=\([^ ]*\).*/\1/p' \
  "$output_dir/capture-summary.txt")
certificate_bytes=$(wc -c <"$certificates")
awk -v begin="$build_begin" -v end="$build_end" \
  -v capture_preparation="$capture_preparation" \
  -v capture_evaluation="$capture_evaluation" \
  -v certificate_bytes="$certificate_bytes" 'BEGIN {
    print "metric\tvalue"
    printf "build_seconds\t%.9f\n", (end - begin) / 1000000000
    printf "capture_preparation_seconds\t%.9f\n", capture_preparation
    printf "capture_evaluation_and_write_seconds\t%.9f\n", capture_evaluation
    printf "certificate_records\t50750\n"
    printf "certificate_bytes\t%d\n", certificate_bytes
  }' >"$output_dir/one-time-costs.tsv"

{
  echo 'status=DEVELOPMENT_NON_RELEASE'
  echo 'held_constant=authenticated_expression_graph,boxes,fixed_scale,endpoint_representation'
  echo 'changed_axis=compute_reciprocal_by_division_vs_validate_supplied_exact_enclosure'
  echo 'bounds_identical=yes'
  echo 'accepted=875/875'
  echo "reordered_certificate_exit=$reordered_exit"
  echo "invalid_certificate_exit=$invalid_exit"
  echo "overflow_certificate_exit=$overflow_exit"
} >"$output_dir/decision.txt"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/nl-native-builtin" "$certificates" \
  "$output_dir/capture-results.txt" "$summaries" \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir"/*-summary.txt "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" "$output_dir/decision.txt" \
  "$output_dir/reordered-certificates.tsv" \
  "$output_dir/invalid-certificates.tsv" \
  "$output_dir/overflow-certificates.tsv" \
  "$output_dir/reordered-stderr.txt" "$output_dir/invalid-stderr.txt" \
  "$output_dir/overflow-stderr.txt" \
  >"$output_dir/result-files.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_RECIPROCAL_CERTIFICATE_PAIRED_OK DEVELOPMENT_NON_RELEASE'
