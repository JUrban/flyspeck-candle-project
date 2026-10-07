#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 PROGRAM.cval JOBS.tsv EXPECTED.tsv OUTPUT-DIR" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
expected=$3
output_dir=$4
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

for input in "$program" "$jobs" "$expected" "$source_file"; do
  [[ -f "$input" ]]
done
[[ -x "$analyzer" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_MIXED_INT128_192=1 -DCANDLE_NL_CASE_ID=16594 \
  -DCANDLE_NL_SQRT_SLOTS=10 -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-mixed"
build_end=$(date +%s%N)

common=(--accept-only --count-fixed-quotients --binary-scale-bits=40 \
  --dyadic-shift-fixed-quotient --sign-specialized-interval-products \
  --specialized-delta-radicands --specialized-delta-derivatives)

/usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
  -o "$output_dir/baseline-resource.txt" \
  "$output_dir/nl-native-mixed" "$program" "$jobs" "$expected" \
  "${common[@]}" >"$output_dir/baseline-results.txt"

set +e
/usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
  -o "$output_dir/candidate-resource.txt" \
  "$output_dir/nl-native-mixed" "$program" "$jobs" "$expected" \
  "${common[@]}" --specialized-delta-inverse-roots \
  >"$output_dir/candidate-results.txt" \
  2>"$output_dir/candidate-stderr.txt"
candidate_exit=$?
set -e

[[ "$candidate_exit" -eq 1 ]]
rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
  "$output_dir/baseline-results.txt" >"$output_dir/baseline-summary.txt"
rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
  "$output_dir/candidate-results.txt" >"$output_dir/candidate-summary.txt"
rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  "$output_dir/baseline-results.txt" >"$output_dir/baseline-bounds.txt"
rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  "$output_dir/candidate-results.txt" >"$output_dir/candidate-bounds.txt"

rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*accepted=875' \
  "$output_dir/baseline-summary.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*specialized_delta_inverse_roots=1 .*accepted=408' \
  "$output_dir/candidate-summary.txt"
rg -q '^development comparison accepted 408 of 875 jobs$' \
  "$output_dir/candidate-stderr.txt"

"$analyzer" "$output_dir/baseline-results.txt" \
  "$output_dir/candidate-results.txt" \
  >"$output_dir/candidate-vs-baseline-bounds.json"

awk -v begin="$build_begin" -v end="$build_end" 'BEGIN {
  print "phase\tseconds";
  printf "build_exact_mixed\t%.9f\n", (end - begin) / 1000000000;
}' >"$output_dir/one-time-costs.tsv"

{
  echo "status=DEVELOPMENT_NON_RELEASE_REJECTED"
  echo "candidate_exit=$candidate_exit"
  echo "expected_candidate_accepted=408"
  echo "source_identity=authenticated_delta_pair"
  echo "held_arithmetic=mixed_checked_int128_192"
  echo "held_scale=2^40"
  echo "changed_boundary=direct_completed_inverse_sqrt"
} >"$output_dir/decision.txt"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/nl-native-mixed" "$output_dir/baseline-results.txt" \
  "$output_dir/candidate-results.txt" "$output_dir/candidate-stderr.txt" \
  "$output_dir/candidate-vs-baseline-bounds.json" \
  "$output_dir/one-time-costs.tsv" "$output_dir/decision.txt" \
  >"$output_dir/result-files.sha256"

cat "$output_dir/baseline-summary.txt"
cat "$output_dir/candidate-summary.txt"
echo "CANDLE_NL_NATIVE_CASE16594_INVERSE_ROOT_REJECTED DEVELOPMENT_NON_RELEASE accepted=408/875"
