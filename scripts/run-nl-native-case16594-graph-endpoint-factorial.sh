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

common=(-std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include")
defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)

build_begin=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_MIXED_INT128_192=1 "${defines[@]}" \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-boost"
build_boost_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_INT128=1 \
  -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 "${defines[@]}" \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-builtin"
build_builtin_end=$(date +%s%N)

lane_options() {
  local lane=$1
  printf '%s\0' --accept-only --count-fixed-quotients \
    --binary-scale-bits=40 --dyadic-shift-fixed-quotient \
    --sign-specialized-interval-products
  if [[ "$lane" == *-specialized ]]; then
    printf '%s\0' --specialized-delta-radicands \
      --specialized-delta-derivatives
  fi
}

lane_binary() {
  local lane=$1
  if [[ "$lane" == boost-* ]]; then
    printf '%s\n' "$output_dir/nl-native-boost"
  else
    printf '%s\n' "$output_dir/nl-native-builtin"
  fi
}

run_lane() {
  local lane=$1 repetition=$2 destination=$3 binary
  local -a options
  binary=$(lane_binary "$lane")
  mapfile -d '' -t options < <(lane_options "$lane")
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(boost-generic boost-specialized builtin-generic builtin-specialized)
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
  binary=$(lane_binary "$lane")
  mapfile -d '' -t options < <(lane_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M' \
    -o "$output_dir/$lane-resource.txt" \
    "$binary" "$program" "$jobs" "$expected" "${options[@]}" \
    >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-summary.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*accepted=875' \
    "$output_dir/$lane-summary.txt"
  rg -q ' sign_specialized_interval_products=1 ' \
    "$output_dir/$lane-summary.txt"
  if [[ "$lane" == *-specialized ]]; then
    rg -q ' specialized_delta_radicands=1 specialized_delta_radicand_count=3 specialized_delta_derivatives=1 specialized_delta_derivative_count=3 ' \
      "$output_dir/$lane-summary.txt"
    rg -q ' mixed_wide_taylor_completions=162750 mixed_wide_narrowings=325500 ' \
      "$output_dir/$lane-summary.txt"
  else
    rg -q ' specialized_delta_radicands=0 specialized_delta_radicand_count=0 specialized_delta_derivatives=0 specialized_delta_derivative_count=0 ' \
      "$output_dir/$lane-summary.txt"
    rg -q ' mixed_wide_taylor_completions=483000 mixed_wide_narrowings=966000 ' \
      "$output_dir/$lane-summary.txt"
  fi
done

cmp "$output_dir/boost-generic-bounds.txt" \
  "$output_dir/builtin-generic-bounds.txt"
cmp "$output_dir/boost-specialized-bounds.txt" \
  "$output_dir/builtin-specialized-bounds.txt"

"$analyzer" "$output_dir/boost-generic-results.txt" \
  "$output_dir/boost-specialized-results.txt" \
  >"$output_dir/boost-specialized-vs-generic-bounds.json"
"$analyzer" "$output_dir/builtin-generic-results.txt" \
  "$output_dir/builtin-specialized-results.txt" \
  >"$output_dir/builtin-specialized-vs-generic-bounds.json"

awk '
  function value(name, i, field) {
    for (i = 1; i <= NF; ++i) {
      split($i, field, "=");
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
    names[1]="boost-generic"; names[2]="boost-specialized"
    names[3]="builtin-generic"; names[4]="builtin-specialized"
    for (i = 1; i <= 4; ++i) {
      lane=names[i]
      p=preparation[lane]/count[lane]; e=evaluation[lane]/count[lane]
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n",lane,count[lane],p,e,p+e,minimum[lane]
    }
    bg=evaluation["boost-generic"]/count["boost-generic"]
    bs=evaluation["boost-specialized"]/count["boost-specialized"]
    ng=evaluation["builtin-generic"]/count["builtin-generic"]
    ns=evaluation["builtin-specialized"]/count["builtin-specialized"]
    bgp=preparation["boost-generic"]/count["boost-generic"]
    bsp=preparation["boost-specialized"]/count["boost-specialized"]
    ngp=preparation["builtin-generic"]/count["builtin-generic"]
    nsp=preparation["builtin-specialized"]/count["builtin-specialized"]
    printf "boost_graph_speedup\t%d\t0\t%.9f\t0\t875\n",count["boost-generic"],bg/bs
    printf "builtin_graph_speedup\t%d\t0\t%.9f\t0\t875\n",count["builtin-generic"],ng/ns
    printf "generic_representation_speedup\t%d\t0\t%.9f\t0\t875\n",count["boost-generic"],bg/ng
    printf "specialized_representation_speedup\t%d\t0\t%.9f\t0\t875\n",count["boost-specialized"],bs/ns
    printf "boost_graph_batch_speedup\t%d\t0\t0\t%.9f\t875\n",count["boost-generic"],(bgp+bg)/(bsp+bs)
    printf "builtin_graph_batch_speedup\t%d\t0\t0\t%.9f\t875\n",count["builtin-generic"],(ngp+ng)/(nsp+ns)
    printf "graph_representation_interaction\t%d\t0\t%.9f\t0\t875\n",count["boost-generic"],(bg/bs)/(ng/ns)
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v boost="$build_boost_end" \
    -v builtin="$build_builtin_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_boost_mixed\t%.9f\n",(boost-begin)/1000000000
  printf "build_builtin_endpoint\t%.9f\n",(builtin-boost)/1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/summaries.txt" "$output_dir"/*-results.txt \
  "$output_dir"/*-bounds.txt "$output_dir"/*-summary.txt \
  "$output_dir"/*-bounds.json "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/result-files.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_GRAPH_ENDPOINT_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
