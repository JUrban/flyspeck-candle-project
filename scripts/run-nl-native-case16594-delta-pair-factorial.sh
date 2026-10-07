#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "usage: $0 PROGRAM.cval JOBS.tsv EXPECTED.tsv OUTPUT-DIR REPETITIONS" >&2
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
for input in "$program" "$jobs" "$expected" "$source_file"; do [[ -f "$input" ]]; done
[[ -x "$analyzer" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

defines=(-DCANDLE_NL_CASE_ID=16594 -DCANDLE_NL_SQRT_SLOTS=10 \
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167)
build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_MIXED_INT128_192=1 "${defines[@]}" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-mixed"
build_mixed_end=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -DCANDLE_NL_FIXED_DOUBLE=1 \
  "${defines[@]}" "$source_file" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-double"
build_double_end=$(date +%s%N)

lane_options() {
  local lane=$1
  printf '%s\0' --accept-only --count-fixed-quotients \
    --binary-scale-bits=40 --specialized-delta-radicands
  [[ "$lane" == exact-* ]] && printf '%s\0' --dyadic-shift-fixed-quotient
  [[ "$lane" == *-pairs ]] && printf '%s\0' --specialized-delta-derivatives
}

run_lane() {
  local lane=$1 repetition=$2 destination=$3 binary
  local -a options
  [[ "$lane" == exact-* ]] && binary="$output_dir/nl-native-mixed" || \
    binary="$output_dir/nl-native-double"
  mapfile -d '' -t options < <(lane_options "$lane")
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(exact-radicands exact-pairs double-radicands double-pairs)
summaries="$output_dir/summaries.txt"
: >"$summaries"
for lane in "${lanes[@]}"; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

for lane in "${lanes[@]}"; do
  [[ "$lane" == exact-* ]] && binary="$output_dir/nl-native-mixed" || \
    binary="$output_dir/nl-native-double"
  mapfile -d '' -t options < <(lane_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M' \
    -o "$output_dir/$lane-resource.txt" \
    "$binary" "$program" "$jobs" "$expected" "${options[@]}" \
    >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' "$output_dir/$lane-results.txt" \
    >"$output_dir/$lane-bounds.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' "$output_dir/$lane-results.txt" \
    >"$output_dir/$lane-summary.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*accepted=875' \
    "$output_dir/$lane-summary.txt"
  rg -q ' specialized_delta_radicands=1 specialized_delta_radicand_count=3 ' \
    "$output_dir/$lane-summary.txt"
  if [[ "$lane" == *-pairs ]]; then
    rg -q ' specialized_delta_derivatives=1 specialized_delta_derivative_count=3 ' \
      "$output_dir/$lane-summary.txt"
  else
    rg -q ' specialized_delta_derivatives=0 specialized_delta_derivative_count=0 ' \
      "$output_dir/$lane-summary.txt"
  fi
done

"$analyzer" "$output_dir/exact-radicands-results.txt" \
  "$output_dir/exact-pairs-results.txt" \
  >"$output_dir/exact-pairs-vs-radicands-bounds.json"
"$analyzer" "$output_dir/double-radicands-results.txt" \
  "$output_dir/double-pairs-results.txt" \
  >"$output_dir/double-pairs-vs-radicands-bounds.json"
"$analyzer" "$output_dir/exact-pairs-results.txt" \
  "$output_dir/double-pairs-results.txt" \
  >"$output_dir/double-vs-exact-pairs-bounds.json"

awk '
  function value(name, i, field) {
    for (i = 1; i <= NF; ++i) {
      split($i, field, "="); if (field[1] == name) return field[2]
    }
  }
  {
    lane = value("lane"); if (lane == "") next
    count[lane]++; preparation[lane] += value("preparation_seconds")
    evaluation[lane] += value("evaluation_seconds")
    accepted = value("accepted") + 0
    if (!(lane in minimum) || accepted < minimum[lane]) minimum[lane] = accepted
  }
  END {
    print "lane\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted"
    names[1]="exact-radicands"; names[2]="exact-pairs"
    names[3]="double-radicands"; names[4]="double-pairs"
    for (i = 1; i <= 4; ++i) {
      lane=names[i]; p=preparation[lane]/count[lane]; e=evaluation[lane]/count[lane]
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane,count[lane],p,e,p+e,minimum[lane]
    }
    er=evaluation["exact-radicands"]/count["exact-radicands"]
    ep=evaluation["exact-pairs"]/count["exact-pairs"]
    dr=evaluation["double-radicands"]/count["double-radicands"]
    dp=evaluation["double-pairs"]/count["double-pairs"]
    printf "exact_derivative_speedup\t%d\t0\t%.9f\t0\t875\n",count["exact-pairs"],er/ep
    printf "double_derivative_speedup\t%d\t0\t%.9f\t0\t875\n",count["double-pairs"],dr/dp
    printf "radicands_exact_over_double\t%d\t0\t%.9f\t0\t875\n",count["exact-radicands"],er/dr
    printf "pairs_exact_over_double\t%d\t0\t%.9f\t0\t875\n",count["exact-pairs"],ep/dp
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v mixed="$build_mixed_end" \
  -v double="$build_double_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_mixed\t%.9f\n",(mixed-begin)/1000000000
  printf "build_double\t%.9f\n",(double-mixed)/1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/nl-native-mixed" "$output_dir/nl-native-double" \
  "$output_dir/summaries.txt" "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" \
  "$output_dir/exact-pairs-vs-radicands-bounds.json" \
  "$output_dir/double-pairs-vs-radicands-bounds.json" \
  "$output_dir/double-vs-exact-pairs-bounds.json" \
  >"$output_dir/result-files.sha256"

cat "$output_dir/phase-times.tsv"
