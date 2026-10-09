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
rg -q 'historical-whole' "$stream_source"
rg -q 'CANDLE_NL_MIXED_INT128_192' "$base_source"
rg -q 'CANDLE_NL_MIXED_NATIVE_INT128_192' "$base_source"

common=(-std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include")
defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)
build_begin=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_CHECKED_INT192=1 "${defines[@]}" \
  "$stream_source" -lgmpxx -lgmp -o "$output_dir/nl-native-wide-checked"
build_wide_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_MIXED_INT128_192=1 "${defines[@]}" \
  "$stream_source" -lgmpxx -lgmp -o "$output_dir/nl-native-boost-checked"
build_boost_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_INT128=1 \
  -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 "${defines[@]}" \
  "$stream_source" -lgmpxx -lgmp -o "$output_dir/nl-native-builtin"
build_builtin_end=$(date +%s%N)

lane_binary() {
  local representation=$1
  case "$representation" in
    wide) printf '%s\n' "$output_dir/nl-native-wide-checked" ;;
    boost) printf '%s\n' "$output_dir/nl-native-boost-checked" ;;
    builtin) printf '%s\n' "$output_dir/nl-native-builtin" ;;
    *) return 2 ;;
  esac
}

lane_mode() {
  local algorithm=$1
  if [[ "$algorithm" == generic ]]; then
    printf '%s\n' dag
  else
    printf '%s\n' historical-whole
  fi
}

run_summary() {
  local representation=$1 algorithm=$2 repetition=$3 destination=$4
  local binary mode
  binary=$(lane_binary "$representation")
  mode=$(lane_mode "$algorithm")
  "$binary" "$program" "$jobs" "$topology" "$mode" |
    rg '^CANDLE_NL_NATIVE_STREAMING_SUMMARY ' |
    sed "s/$/ representation_lane=$representation algorithm_lane=$algorithm repetition=$repetition/" \
      >>"$destination"
}

lanes=(wide-generic wide-historical boost-historical builtin-historical)
summaries="$output_dir/summaries.txt"
: >"$summaries"
for lane in "${lanes[@]}"; do
  representation=${lane%%-*}
  algorithm=${lane#*-}
  run_summary "$representation" "$algorithm" warmup /dev/null
done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % 4))
  for ((offset = 0; offset < 4; ++offset)); do
    lane=${lanes[$(((rotation + offset) % 4))]}
    representation=${lane%%-*}
    algorithm=${lane#*-}
    run_summary "$representation" "$algorithm" "$repetition" "$summaries"
  done
done

for lane in "${lanes[@]}"; do
  representation=${lane%%-*}
  algorithm=${lane#*-}
  binary=$(lane_binary "$representation")
  mode=$(lane_mode "$algorithm")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$representation-$algorithm-resource.txt" \
    "$binary" "$program" "$jobs" "$topology" "$mode" \
    >"$output_dir/$representation-$algorithm-results.txt"
  rg '^CANDLE_NL_NATIVE_STREAMING_RESULT ' \
    "$output_dir/$representation-$algorithm-results.txt" \
    >"$output_dir/$representation-$algorithm-decisions.txt"
  rg -q "^CANDLE_NL_NATIVE_STREAMING_FOREST_OK DEVELOPMENT_NON_RELEASE mode=$mode$" \
    "$output_dir/$representation-$algorithm-results.txt"
  expected_visits=9994
  [[ "$algorithm" == historical ]] && expected_visits=1302
  rg -q "^CANDLE_NL_NATIVE_STREAMING_SUMMARY mode=$mode .*total_nodes=11718 components=20 visited_nodes=$expected_visits .*rejected_leaves=0 " \
    "$output_dir/$representation-$algorithm-results.txt"
done
cmp "$output_dir/wide-historical-decisions.txt" \
    "$output_dir/boost-historical-decisions.txt"
cmp "$output_dir/wide-historical-decisions.txt" \
    "$output_dir/builtin-historical-decisions.txt"

awk '
  function value(name,i,field) {
    for (i=1;i<=NF;++i) {
      split($i,field,"="); if (field[1]==name) return field[2]
    }
  }
  {
    representation=value("representation_lane")
    algorithm=value("algorithm_lane")
    if (representation == "" || algorithm == "") next
    key=representation "-" algorithm
    count[key]++
    visited[key]=value("visited_nodes")
    input[key]+=value("input_seconds")
    preparation[key]+=value("reusable_preparation_seconds")
    traversal[key]+=value("traversal_seconds")
    total[key]+=value("total_seconds")
  }
  END {
    print "representation\talgorithm\truns\tvisited_nodes\tmean_input_seconds\tmean_reusable_preparation_seconds\tmean_traversal_seconds\tmean_total_seconds"
    lanes[1]="wide-generic"; lanes[2]="wide-historical"
    lanes[3]="boost-historical"; lanes[4]="builtin-historical"
    for (i=1;i<=4;++i) {
      key=lanes[i]
      split(key,parts,"-")
      printf "%s\t%s\t%d\t%d\t%.9f\t%.9f\t%.9f\t%.9f\n", \
        parts[1],parts[2],count[key],visited[key], \
        input[key]/count[key],preparation[key]/count[key], \
        traversal[key]/count[key],total[key]/count[key]
    }
    wg=traversal["wide-generic"]/count["wide-generic"]
    wh=traversal["wide-historical"]/count["wide-historical"]
    bh=traversal["boost-historical"]/count["boost-historical"]
    nh=traversal["builtin-historical"]/count["builtin-historical"]
    wgt=total["wide-generic"]/count["wide-generic"]
    wht=total["wide-historical"]/count["wide-historical"]
    bht=total["boost-historical"]/count["boost-historical"]
    nht=total["builtin-historical"]/count["builtin-historical"]
    printf "wide\thistorical_over_generic_speedup\t%d\t%d\t0\t0\t%.9f\t%.9f\n",count["wide-generic"],visited["wide-historical"],wg/wh,wgt/wht
    printf "representation\thistorical_boost_over_builtin\t%d\t%d\t0\t0\t%.9f\t%.9f\n",count["boost-historical"],visited["builtin-historical"],bh/nh,bht/nht
    printf "range_control\thistorical_wide_over_builtin\t%d\t%d\t0\t0\t%.9f\t%.9f\n",count["wide-historical"],visited["builtin-historical"],wh/nh,wht/nht
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v wide="$build_wide_end" -v boost="$build_boost_end" \
    -v builtin="$build_builtin_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_wide_checked\t%.9f\n",(wide-begin)/1e9
  printf "build_boost_checked\t%.9f\n",(boost-wide)/1e9
  printf "build_builtin\t%.9f\n",(builtin-boost)/1e9
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$base_source" "$stream_source" "$program" "$jobs" \
  "$topology" "$output_dir/source-revision.txt" "$output_dir/summaries.txt" \
  "$output_dir"/*-results.txt "$output_dir"/*-decisions.txt \
  "$output_dir"/*-resource.txt "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/evidence.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_EXACT_REPRESENTATION_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
