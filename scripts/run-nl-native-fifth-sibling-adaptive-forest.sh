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
analyzer="$repo_root/scripts/analyze-nl-adaptive-forest.py"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
source_revision=${CANDLE_NL_NATIVE_SOURCE_REVISION:-2ab9436}
source_path=tools/nl_native_fixed_scale_case10173.cc

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ "$expected_nodes" =~ ^[1-9][0-9]*$ ]]
[[ "$expected_components" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$jobs" "$topology"; do [[ -f "$input" ]]; done
[[ -x "$analyzer" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq "$expected_nodes" ]]
[[ $(wc -l <"$topology") -eq "$expected_nodes" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

resolved_source_revision=$(git -C "$repo_root" rev-parse "$source_revision^{commit}")
source_file="$output_dir/nl_native_fixed_scale_case10173.cc"
git -C "$repo_root" show "$resolved_source_revision:$source_path" >"$source_file"
printf 'revision=%s\npath=%s\n' "$resolved_source_revision" "$source_path" \
  >"$output_dir/source-revision.txt"
rg -q -- '--source-dag-cache' "$source_file"
rg -q -- '--specialized-delta-historical-dihedrals' "$source_file"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_FIXED_INT128=1 -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 \
  -DCANDLE_NL_CASE_ID=16594 -DCANDLE_NL_SQRT_SLOTS=10 \
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-exact"
build_end=$(date +%s%N)

lane_options() {
  local lane=$1
  printf '%s\0' --count-fixed-quotients \
    --binary-scale-bits=40 --sign-specialized-interval-products \
    --fixed-sqrt-inverse-kernels --fixed-atan-kernel \
    --taylor-reconstructed-box --specialized-delta-radicands \
    --specialized-delta-derivatives --prepared-simple-polynomials \
    --source-dag-cache --dyadic-shift-fixed-quotient \
    --computed-tight-sqrt-certificates --allow-rejected-development \
    --subdivide-domain-failures-development
  [[ "$lane" == historical ]] && \
    printf '%s\0' --specialized-delta-historical-dihedrals
}

zero_expected() {
  local count=$1 destination=$2
  awk -v count="$count" 'BEGIN { for (i = 0; i < count; ++i) print i "\t0" }' \
    >"$destination"
}

all_expected="$output_dir/all-zero-expected.tsv"
zero_expected "$expected_nodes" "$all_expected"
for lane in dag historical; do
  mapfile -d '' -t options < <(lane_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/all-$lane-resource.txt" \
    "$output_dir/nl-native-exact" "$program" "$jobs" "$all_expected" \
    "${options[@]}" >"$output_dir/all-$lane-results.txt"
  rg -q "^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=$expected_nodes .*source_dag_cache=1 .*computed_tight_sqrt_certificates=1 .*case_id=16594 " \
    "$output_dir/all-$lane-results.txt"
  [[ $(rg -c '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
       "$output_dir/all-$lane-results.txt") -eq "$expected_nodes" ]]
  "$analyzer" "$topology" "$output_dir/all-$lane-results.txt" "$jobs" \
    "$output_dir/$lane-adaptive-jobs.tsv" \
    "$output_dir/$lane-adaptive-summary.json" \
    >"$output_dir/$lane-adaptive-summary-line.json"
  jq -e --argjson components "$expected_components" \
    '.complete_acceptance == true and .components == $components and
     .visited_nodes + .skipped_nodes == .total_nodes' \
    "$output_dir/$lane-adaptive-summary.json" >/dev/null
  count=$(jq -r '.visited_nodes' "$output_dir/$lane-adaptive-summary.json")
  [[ $(wc -l <"$output_dir/$lane-adaptive-jobs.tsv") -eq "$count" ]]
  zero_expected "$count" "$output_dir/$lane-adaptive-zero-expected.tsv"
done

run_lane() {
  local lane=$1 repetition=$2 destination=$3
  local -a options
  mapfile -d '' -t options < <(lane_options "$lane")
  "$output_dir/nl-native-exact" "$program" \
    "$output_dir/$lane-adaptive-jobs.tsv" \
    "$output_dir/$lane-adaptive-zero-expected.tsv" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane dag warmup /dev/null
run_lane historical warmup /dev/null
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then lanes=(dag historical); else lanes=(historical dag); fi
  for lane in "${lanes[@]}"; do run_lane "$lane" "$repetition" "$summaries"; done
done

for lane in dag historical; do
  mapfile -d '' -t options < <(lane_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-adaptive-resource.txt" \
    "$output_dir/nl-native-exact" "$program" \
    "$output_dir/$lane-adaptive-jobs.tsv" \
    "$output_dir/$lane-adaptive-zero-expected.tsv" "${options[@]}" \
    >"$output_dir/$lane-adaptive-results.txt"
done

dag_nodes=$(jq -r '.visited_nodes' "$output_dir/dag-adaptive-summary.json")
historical_nodes=$(jq -r '.visited_nodes' \
  "$output_dir/historical-adaptive-summary.json")
awk -v dag_nodes="$dag_nodes" -v historical_nodes="$historical_nodes" '
  function value(name, i, field) {
    for (i = 1; i <= NF; ++i) {
      split($i, field, "="); if (field[1] == name) return field[2]
    }
  }
  {
    lane=value("lane"); if (lane == "") next
    count[lane]++
    preparation[lane]+=value("preparation_seconds")
    evaluation[lane]+=value("evaluation_seconds")
  }
  END {
    print "lane\truns\tvisited_nodes\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds"
    names[1]="dag"; names[2]="historical"
    nodes["dag"]=dag_nodes; nodes["historical"]=historical_nodes
    for (i=1; i<=2; ++i) {
      lane=names[i]; p=preparation[lane]/count[lane]
      e=evaluation[lane]/count[lane]
      printf "%s\t%d\t%d\t%.9f\t%.9f\t%.9f\n",lane,count[lane],nodes[lane],p,e,p+e
    }
    dp=preparation["dag"]/count["dag"]
    de=evaluation["dag"]/count["dag"]
    hp=preparation["historical"]/count["historical"]
    he=evaluation["historical"]/count["historical"]
    printf "historical_vs_dag\t%d\t%d\t0\t%.9f\t%.9f\n",count["dag"],historical_nodes,de/he,(dp+de)/(hp+he)
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v end="$build_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_exact\t%.9f\n",(end-begin)/1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$analyzer" "$source_file" "$program" "$jobs" "$topology" \
  "$output_dir/source-revision.txt" "$output_dir"/all-*-results.txt \
  "$output_dir"/*-adaptive-summary.json "$output_dir"/*-adaptive-jobs.tsv \
  "$output_dir/summaries.txt" "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/evidence.sha256"

cat "$output_dir/dag-adaptive-summary-line.json"
cat "$output_dir/historical-adaptive-summary-line.json"
cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_ADAPTIVE_FOREST_OK DEVELOPMENT_NON_RELEASE'
