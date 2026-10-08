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
  -DCANDLE_NL_FIXED_INT128=1 -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 \
  -DCANDLE_NL_CASE_ID=16594 -DCANDLE_NL_SQRT_SLOTS=10 \
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-exact"
build_end=$(date +%s%N)

lane_options() {
  local lane=$1
  printf '%s\0' --accept-only --count-fixed-quotients \
    --binary-scale-bits=40 --dyadic-shift-fixed-quotient \
    --sign-specialized-interval-products \
    --fixed-sqrt-inverse-kernels --fixed-atan-kernel \
    --taylor-reconstructed-box --specialized-delta-radicands \
    --specialized-delta-derivatives
  if [[ "$lane" == identity || "$lane" == identity-u ]]; then
    printf '%s\0' --specialized-delta-dihedral-identities
  fi
  if [[ "$lane" == identity-u ]]; then
    printf '%s\0' --optimized-dihedral-u-bounds
  fi
}

run_lane() {
  local lane=$1 repetition=$2 destination=$3
  local -a options
  mapfile -d '' -t options < <(lane_options "$lane")
  "$output_dir/nl-native-exact" "$program" "$jobs" "$expected" \
    "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(sequential identity identity-u)
summaries="$output_dir/summaries.txt"
: >"$summaries"
for lane in "${lanes[@]}"; do
  run_lane "$lane" warmup /dev/null
done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

for lane in "${lanes[@]}"; do
  mapfile -d '' -t options < <(lane_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-resource.txt" \
    "$output_dir/nl-native-exact" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-summary.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*accepted=875' \
    "$output_dir/$lane-summary.txt"
done

rg -q ' specialized_delta_dihedral_identities=0 specialized_delta_dihedral_chain_count=0 ' \
  "$output_dir/sequential-summary.txt"
rg -q ' specialized_delta_dihedral_identities=1 specialized_delta_dihedral_chain_count=3 ' \
  "$output_dir/identity-summary.txt"
rg -q ' optimized_dihedral_u_bounds=1 .*specialized_delta_dihedral_identities=1 specialized_delta_dihedral_chain_count=3 ' \
  "$output_dir/identity-u-summary.txt"

# A separate, uncharged diagnostic recomputes the original authenticated
# eight-operation chains and requires overlap of every center value,
# derivative, box value/gradient, and Hessian enclosure on all 875 cells.
mapfile -d '' -t overlap_options < <(lane_options identity)
"$output_dir/nl-native-exact" "$program" "$jobs" "$expected" \
  "${overlap_options[@]}" --verify-fixed-kernel-enclosures \
  >"$output_dir/identity-overlap-results.txt"
rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
  "$output_dir/identity-overlap-results.txt" \
  >"$output_dir/identity-overlap-summary.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*verify_fixed_kernel_enclosures=1 .*accepted=875' \
  "$output_dir/identity-overlap-summary.txt"

awk '
  function value(name, i, field) {
    for (i = 1; i <= NF; ++i) {
      split($i, field, "="); if (field[1] == name) return field[2]
    }
  }
  {
    lane = value("lane"); if (lane == "") next
    count[lane]++
    preparation[lane] += value("preparation_seconds")
    evaluation[lane] += value("evaluation_seconds")
    accepted = value("accepted") + 0
    products[lane] = value("interval_products") + 0
    completions[lane] = value("completed_results") + 0
    if (!(lane in minimum) || accepted < minimum[lane]) minimum[lane] = accepted
  }
  END {
    print "lane\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted\tinterval_products\tcompleted_results\trecurring_speedup"
    names[1] = "sequential"; names[2] = "identity"; names[3] = "identity-u"
    baseline = evaluation["sequential"] / count["sequential"]
    for (i = 1; i <= 3; ++i) {
      lane = names[i]
      p = preparation[lane] / count[lane]
      e = evaluation[lane] / count[lane]
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\t%d\t%d\t%.6f\n", \
        lane, count[lane], p, e, p + e, minimum[lane], products[lane], \
        completions[lane], baseline / e
    }
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v end="$build_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_exact\t%.9f\n", (end - begin) / 1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/summaries.txt" "$output_dir"/*-results.txt \
  "$output_dir"/*-bounds.txt "$output_dir"/*-summary.txt \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/evidence.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_DIHEDRAL_IDENTITIES_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
