#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv TOPOLOGY.tsv OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
topology=$3
output_dir=$4
repetitions=$5
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
source_revision=${CANDLE_NL_NATIVE_SOURCE_REVISION:-HEAD}
base_source_path=tools/nl_native_fixed_scale_case10173.cc
stream_source_path=tools/nl_native_case16594_streaming_forest.cc
baseline_decisions_sha256=aafedb92ca6046ef4a75cb9e31c484f2864381023ea966bd1539019b732e7a85

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$jobs" "$topology"; do [[ -f "$input" ]]; done
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq 11718 ]]
[[ $(wc -l <"$topology") -eq 11718 ]]
[[ $(sha256sum "$program" | cut -d' ' -f1) == \
   82f5c7f81b7a6ec292b6426caddaddb1ce7fde5dfbd83c2900a072f679a28dcb ]]
[[ $(sha256sum "$jobs" | cut -d' ' -f1) == \
   3bee088af91059dd37e9812ccc4945498dd29e7c616e82c66ba8bc4ae4eac896 ]]
[[ $(sha256sum "$topology" | cut -d' ' -f1) == \
   2a710c2b1e845ff24aad9eb56b45c8436eb0bd86db64559a1dba63f7c70f5fd3 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

resolved_revision=$(git -C "$repo_root" rev-parse "$source_revision^{commit}")
base_source="$output_dir/nl_native_fixed_scale_case10173.cc"
stream_source="$output_dir/nl_native_case16594_streaming_forest.cc"
git -C "$repo_root" show "$resolved_revision:$base_source_path" >"$base_source"
git -C "$repo_root" show "$resolved_revision:$stream_source_path" >"$stream_source"
printf 'revision=%s\nbase_path=%s\nstream_path=%s\n' \
  "$resolved_revision" "$base_source_path" "$stream_source_path" \
  >"$output_dir/source-revision.txt"
rg -q 'historical-whole-monotone' "$stream_source"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_CHECKED_INT192=1 \
  -DCANDLE_NL_CASE_ID=16594 -DCANDLE_NL_SQRT_SLOTS=10 \
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$stream_source" -lgmpxx -lgmp -o "$output_dir/nl-native-wide-checked"
build_end=$(date +%s%N)

lane_mode() {
  case "$1" in
    baseline) printf '%s\n' historical-whole ;;
    monotone) printf '%s\n' historical-whole-monotone ;;
    *) return 2 ;;
  esac
}

run_summary() {
  local lane=$1 repetition=$2 destination=$3 mode
  mode=$(lane_mode "$lane")
  "$output_dir/nl-native-wide-checked" \
    "$program" "$jobs" "$topology" "$mode" |
    rg '^CANDLE_NL_NATIVE_STREAMING_SUMMARY ' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_summary baseline warmup /dev/null
run_summary monotone warmup /dev/null
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if (( repetition % 2 == 1 )); then
    lanes=(baseline monotone)
  else
    lanes=(monotone baseline)
  fi
  for lane in "${lanes[@]}"; do
    run_summary "$lane" "$repetition" "$summaries"
  done
done

for lane in baseline monotone; do
  mode=$(lane_mode "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-resource.txt" \
    "$output_dir/nl-native-wide-checked" \
      "$program" "$jobs" "$topology" "$mode" \
    >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_STREAMING_RESULT ' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-decisions.txt"
  rg -q "^CANDLE_NL_NATIVE_STREAMING_FOREST_OK DEVELOPMENT_NON_RELEASE mode=$mode$" \
    "$output_dir/$lane-results.txt"
  rg -q "^CANDLE_NL_NATIVE_STREAMING_SUMMARY mode=$mode .*total_nodes=11718 components=20 .*rejected_leaves=0 " \
    "$output_dir/$lane-results.txt"
done
[[ $(sha256sum "$output_dir/baseline-decisions.txt" | cut -d' ' -f1) == \
   "$baseline_decisions_sha256" ]]
baseline_visits=$(sed -n 's/.* visited_nodes=\([0-9][0-9]*\) .*/\1/p' \
  "$output_dir/baseline-results.txt")
monotone_visits=$(sed -n 's/.* visited_nodes=\([0-9][0-9]*\) .*/\1/p' \
  "$output_dir/monotone-results.txt")
[[ "$baseline_visits" -eq 1302 ]]
[[ "$monotone_visits" -gt 0 && "$monotone_visits" -le "$baseline_visits" ]]

awk '
  function value(name,i,field) {
    for (i=1;i<=NF;++i) {
      split($i,field,"="); if (field[1]==name) return field[2]
    }
  }
  {
    lane=value("lane")
    if (lane == "") next
    count[lane]++
    visited[lane]=value("visited_nodes")
    rechecks[lane]=value("monotone_face_rechecks")
    coordinates[lane]=value("monotone_restricted_coordinates")
    new_prunes[lane]=value("monotone_new_prunes")
    input[lane]+=value("input_seconds")
    preparation[lane]+=value("reusable_preparation_seconds")
    traversal[lane]+=value("traversal_seconds")
    total[lane]+=value("total_seconds")
  }
  END {
    print "lane\truns\tvisited_nodes\tface_rechecks\trestricted_coordinates\tnew_prunes\tmean_input_seconds\tmean_reusable_preparation_seconds\tmean_traversal_seconds\tmean_total_seconds"
    names[1]="baseline"; names[2]="monotone"
    for (i=1;i<=2;++i) {
      lane=names[i]
      printf "%s\t%d\t%d\t%d\t%d\t%d\t%.9f\t%.9f\t%.9f\t%.9f\n", \
        lane,count[lane],visited[lane],rechecks[lane],coordinates[lane], \
        new_prunes[lane],input[lane]/count[lane], \
        preparation[lane]/count[lane],traversal[lane]/count[lane], \
        total[lane]/count[lane]
    }
    bt=traversal["baseline"]/count["baseline"]
    mt=traversal["monotone"]/count["monotone"]
    btotal=total["baseline"]/count["baseline"]
    mtotal=total["monotone"]/count["monotone"]
    printf "factor\tmonotone_over_baseline\t%d\t%d\t%d\t%d\t0\t0\t%.9f\t%.9f\n", \
      count["monotone"],visited["monotone"],rechecks["monotone"], \
      new_prunes["monotone"],bt/mt,btotal/mtotal
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v end="$build_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_wide_checked\t%.9f\n",(end-begin)/1e9
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$base_source" "$stream_source" "$program" "$jobs" \
  "$topology" "$output_dir/source-revision.txt" "$summaries" \
  "$output_dir"/*-results.txt "$output_dir"/*-decisions.txt \
  "$output_dir"/*-resource.txt "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/evidence.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_MONOTONE_FACE_PAIRED_OK DEVELOPMENT_NON_RELEASE'
