#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 7 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv TOPOLOGY.tsv OUTPUT-DIR REPETITIONS EXPECTED-NODES EXPECTED-COMPONENTS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
topology=$3
output_dir=$4
repetitions=$5
expected_nodes=$6
expected_components=$7
analyzer="$repo_root/scripts/analyze-nl-streaming-forest.py"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
source_revision=${CANDLE_NL_NATIVE_SOURCE_REVISION:-HEAD}
base_source_path=tools/nl_native_fixed_scale_case10173.cc
stream_source_path=tools/nl_native_case16594_streaming_forest.cc

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ "$expected_nodes" =~ ^[1-9][0-9]*$ ]]
[[ "$expected_components" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$jobs" "$topology"; do [[ -f "$input" ]]; done
[[ -x "$analyzer" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq "$expected_nodes" ]]
[[ $(wc -l <"$topology") -eq "$expected_nodes" ]]
[[ $(sha256sum "$program" | cut -d' ' -f1) == \
   82f5c7f81b7a6ec292b6426caddaddb1ce7fde5dfbd83c2900a072f679a28dcb ]]
[[ $(sha256sum "$jobs" | cut -d' ' -f1) == \
   3bee088af91059dd37e9812ccc4945498dd29e7c616e82c66ba8bc4ae4eac896 ]]
[[ $(sha256sum "$topology" | cut -d' ' -f1) == \
   2a710c2b1e845ff24aad9eb56b45c8436eb0bd86db64559a1dba63f7c70f5fd3 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

resolved_source_revision=$(git -C "$repo_root" rev-parse "$source_revision^{commit}")
base_source="$output_dir/nl_native_fixed_scale_case10173.cc"
stream_source="$output_dir/nl_native_case16594_streaming_forest.cc"
git -C "$repo_root" show "$resolved_source_revision:$base_source_path" \
  >"$base_source"
git -C "$repo_root" show "$resolved_source_revision:$stream_source_path" \
  >"$stream_source"
printf 'revision=%s\nbase_path=%s\nstream_path=%s\n' \
  "$resolved_source_revision" "$base_source_path" "$stream_source_path" \
  >"$output_dir/source-revision.txt"
rg -q 'CANDLE_NL_NATIVE_STREAMING_SUMMARY' "$stream_source"

common=(-std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include")
defines=(
  -DCANDLE_NL_FIXED_INT128=1
  -DCANDLE_NL_MIXED_NATIVE_INT128_192=1
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)
build_begin=$(date +%s%N)
g++ "${common[@]}" "${defines[@]}" "$base_source" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-all-node"
build_base_end=$(date +%s%N)
g++ "${common[@]}" "${defines[@]}" "$stream_source" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-streaming"
build_stream_end=$(date +%s%N)

base_options() {
  local lane=$1
  printf '%s\0' --count-fixed-quotients --binary-scale-bits=40 \
    --dyadic-shift-fixed-quotient --sign-specialized-interval-products \
    --fixed-sqrt-inverse-kernels --fixed-atan-kernel \
    --taylor-reconstructed-box --specialized-delta-radicands \
    --specialized-delta-derivatives --prepared-simple-polynomials \
    --source-dag-cache --computed-tight-sqrt-certificates \
    --allow-rejected-development --subdivide-domain-failures-development
  [[ "$lane" == historical ]] && \
    printf '%s\0' --specialized-delta-historical-dihedrals
}

zero_expected="$output_dir/all-zero-expected.tsv"
awk -v count="$expected_nodes" \
  'BEGIN { for (i=0; i<count; ++i) print i "\t0" }' \
  >"$zero_expected"

all_node_begin=$(date +%s%N)
for lane in dag historical; do
  mapfile -d '' -t options < <(base_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/all-$lane-resource.txt" \
    "$output_dir/nl-native-all-node" "$program" "$jobs" \
    "$zero_expected" "${options[@]}" \
    >"$output_dir/all-$lane-results.txt"
  rg -q "^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=$expected_nodes .*case_id=16594 " \
    "$output_dir/all-$lane-results.txt"
  [[ $(rg -c '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT ' \
       "$output_dir/all-$lane-results.txt") -eq "$expected_nodes" ]]
done
all_node_end=$(date +%s%N)

for lane in dag historical; do
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-validation-resource.txt" \
    "$output_dir/nl-native-streaming" "$program" "$jobs" "$topology" \
    "$lane" >"$output_dir/$lane-validation-results.txt"
  "$analyzer" "$topology" "$output_dir/all-$lane-results.txt" \
    "$output_dir/$lane-validation-results.txt" \
    "$output_dir/$lane-validation.json" \
    >"$output_dir/$lane-validation-line.json"
  jq -e --arg lane "$lane" --argjson nodes "$expected_nodes" \
    --argjson components "$expected_components" \
    '.complete_acceptance == true and
     .bounds_and_order_match_all_node_oracle == true and
     .mode == $lane and .total_nodes == $nodes and
     .components == $components and .rejected_leaves == 0' \
    "$output_dir/$lane-validation.json" >/dev/null
done
[[ $(jq -r '.visited_nodes' "$output_dir/dag-validation.json") -eq 9896 ]]
[[ $(jq -r '.visited_nodes' "$output_dir/historical-validation.json") -eq 1344 ]]

run_summary() {
  local lane=$1 repetition=$2 destination=$3
  "$output_dir/nl-native-streaming" "$program" "$jobs" "$topology" \
    "$lane" | rg '^CANDLE_NL_NATIVE_STREAMING_SUMMARY ' |
    sed "s/$/ repetition=$repetition/" >>"$destination"
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_summary dag warmup /dev/null
run_summary historical warmup /dev/null
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    lanes=(dag historical)
  else
    lanes=(historical dag)
  fi
  for lane in "${lanes[@]}"; do
    run_summary "$lane" "$repetition" "$summaries"
  done
done

awk '
  function value(name, i, field) {
    for (i=1; i<=NF; ++i) {
      split($i, field, "="); if (field[1] == name) return field[2]
    }
  }
  {
    lane=value("mode"); if (lane == "") next
    count[lane]++
    visited[lane]=value("visited_nodes")
    input[lane]+=value("input_seconds")
    preparation[lane]+=value("reusable_preparation_seconds")
    traversal[lane]+=value("traversal_seconds")
    total[lane]+=value("total_seconds")
  }
  END {
    print "lane\truns\tvisited_nodes\tmean_input_seconds\tmean_reusable_preparation_seconds\tmean_traversal_seconds\tmean_total_seconds"
    names[1]="dag"; names[2]="historical"
    for (i=1; i<=2; ++i) {
      lane=names[i]
      printf "%s\t%d\t%d\t%.9f\t%.9f\t%.9f\t%.9f\n", \
        lane,count[lane],visited[lane],input[lane]/count[lane], \
        preparation[lane]/count[lane],traversal[lane]/count[lane], \
        total[lane]/count[lane]
    }
    dt=traversal["dag"]/count["dag"]
    ht=traversal["historical"]/count["historical"]
    da=total["dag"]/count["dag"]
    ha=total["historical"]/count["historical"]
    printf "historical_vs_dag\t%d\t%d\t0\t0\t%.9f\t%.9f\n", \
      count["dag"],visited["historical"],dt/ht,da/ha
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v base="$build_base_end" \
  -v stream="$build_stream_end" -v oracle_begin="$all_node_begin" \
  -v oracle_end="$all_node_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_all_node\t%.9f\n",(base-begin)/1000000000
  printf "build_streaming\t%.9f\n",(stream-base)/1000000000
  printf "one_time_all_node_oracles\t%.9f\n", \
    (oracle_end-oracle_begin)/1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$analyzer" "$base_source" "$stream_source" \
  "$program" "$jobs" "$topology" "$output_dir/source-revision.txt" \
  "$output_dir"/all-*-results.txt "$output_dir"/*-validation-results.txt \
  "$output_dir"/*-validation.json "$output_dir/summaries.txt" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  "$output_dir"/*-resource.txt >"$output_dir/evidence.sha256"

cat "$output_dir/dag-validation-line.json"
cat "$output_dir/historical-validation-line.json"
cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_STREAMING_FOREST_OK DEVELOPMENT_NON_RELEASE'
