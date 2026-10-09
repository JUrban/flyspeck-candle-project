#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 7 ]]; then
  printf 'usage: %s PROGRAM.cval HISTORICAL-JOBS.tsv EXPECTED.tsv FULL-JOBS.tsv TOPOLOGY.tsv OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
historical_jobs=$2
expected=$3
full_jobs=$4
topology=$5
output_dir=$6
repetitions=$7
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
source_revision=${CANDLE_NL_NATIVE_SOURCE_REVISION:-HEAD}
base_path=tools/nl_native_fixed_scale_case10173.cc
stream_path=tools/nl_native_case16594_streaming_forest.cc
analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$historical_jobs" "$expected" "$full_jobs" \
  "$topology"; do [[ -f "$input" ]]; done
[[ -x "$analyzer" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$historical_jobs") -eq 1344 ]]
[[ $(wc -l <"$expected") -eq 1344 ]]
[[ $(wc -l <"$full_jobs") -eq 11718 ]]
[[ $(wc -l <"$topology") -eq 11718 ]]
[[ $(sha256sum "$program" | cut -d' ' -f1) == \
   82f5c7f81b7a6ec292b6426caddaddb1ce7fde5dfbd83c2900a072f679a28dcb ]]
[[ $(sha256sum "$historical_jobs" | cut -d' ' -f1) == \
   aee9627da2ca282eb8f32289c2c47d79da99afc517ea883ce8f59566ab660f2a ]]
[[ $(sha256sum "$full_jobs" | cut -d' ' -f1) == \
   3bee088af91059dd37e9812ccc4945498dd29e7c616e82c66ba8bc4ae4eac896 ]]
[[ $(sha256sum "$topology" | cut -d' ' -f1) == \
   2a710c2b1e845ff24aad9eb56b45c8436eb0bd86db64559a1dba63f7c70f5fd3 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

resolved_revision=$(git -C "$repo_root" rev-parse "$source_revision^{commit}")
base_source="$output_dir/nl_native_fixed_scale_case10173.cc"
stream_source="$output_dir/nl_native_case16594_streaming_forest.cc"
git -C "$repo_root" show "$resolved_revision:$base_path" >"$base_source"
git -C "$repo_root" show "$resolved_revision:$stream_path" >"$stream_source"
printf 'revision=%s\nbase_path=%s\nstream_path=%s\n' \
  "$resolved_revision" "$base_path" "$stream_path" \
  >"$output_dir/source-revision.txt"
rg -q -- '--whole-box-jet' "$base_source"
rg -q 'historical-whole' "$stream_source"

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
  -o "$output_dir/nl-native-batch"
build_batch_end=$(date +%s%N)
g++ "${common[@]}" "${defines[@]}" "$stream_source" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-streaming"
build_stream_end=$(date +%s%N)

batch_options() {
  local lane=$1
  printf '%s\0' --count-fixed-quotients --binary-scale-bits=40 \
    --dyadic-shift-fixed-quotient --sign-specialized-interval-products \
    --fixed-sqrt-inverse-kernels --fixed-atan-kernel \
    --taylor-reconstructed-box --specialized-delta-radicands \
    --specialized-delta-derivatives --prepared-simple-polynomials \
    --source-dag-cache --computed-tight-sqrt-certificates \
    --allow-rejected-development --subdivide-domain-failures-development \
    --specialized-delta-historical-dihedrals
  [[ "$lane" == whole ]] && printf '%s\0' --whole-box-jet
}

run_batch_summary() {
  local lane=$1 repetition=$2 destination=$3
  local -a options
  mapfile -d '' -t options < <(batch_options "$lane")
  "$output_dir/nl-native-batch" "$program" "$historical_jobs" \
    "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY ' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

run_stream_summary() {
  local lane=$1 repetition=$2 destination=$3 mode=historical
  [[ "$lane" == whole ]] && mode=historical-whole
  "$output_dir/nl-native-streaming" "$program" "$full_jobs" "$topology" \
    "$mode" | rg '^CANDLE_NL_NATIVE_STREAMING_SUMMARY ' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

batch_summaries="$output_dir/batch-summaries.txt"
stream_summaries="$output_dir/stream-summaries.txt"
: >"$batch_summaries"
: >"$stream_summaries"
for lane in baseline whole; do
  run_batch_summary "$lane" warmup /dev/null
  run_stream_summary "$lane" warmup /dev/null
done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then lanes=(baseline whole); else lanes=(whole baseline); fi
  for lane in "${lanes[@]}"; do
    run_batch_summary "$lane" "$repetition" "$batch_summaries"
    run_stream_summary "$lane" "$repetition" "$stream_summaries"
  done
done

for lane in baseline whole; do
  mapfile -d '' -t options < <(batch_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-batch-resource.txt" \
    "$output_dir/nl-native-batch" "$program" "$historical_jobs" \
    "$expected" "${options[@]}" >"$output_dir/$lane-batch-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT ' \
    "$output_dir/$lane-batch-results.txt" >"$output_dir/$lane-bounds.txt"

  mode=historical
  [[ "$lane" == whole ]] && mode=historical-whole
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-stream-resource.txt" \
    "$output_dir/nl-native-streaming" "$program" "$full_jobs" "$topology" \
    "$mode" >"$output_dir/$lane-stream-results.txt"
  rg '^CANDLE_NL_NATIVE_STREAMING_RESULT ' \
    "$output_dir/$lane-stream-results.txt" >"$output_dir/$lane-stream-decisions.txt"
  rg -q '^CANDLE_NL_NATIVE_STREAMING_SUMMARY .*rejected_leaves=0 .*domain_subdivisions=84 .*maximum_depth=13 ' \
    "$output_dir/$lane-stream-results.txt"
done

rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=1344 .*whole_box_jet=0 .*domain_failure_subdivisions=84 .*accepted=682 ' \
  "$output_dir/baseline-batch-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=1344 .*whole_box_jet=1 .*domain_failure_subdivisions=84 .*accepted=703 ' \
  "$output_dir/whole-batch-results.txt"
rg -q '^CANDLE_NL_NATIVE_STREAMING_SUMMARY .*mode=historical .*visited_nodes=1344 .*terminal_nodes=682 .*rejected_leaves=0 ' \
  "$output_dir/baseline-stream-results.txt"
rg -q '^CANDLE_NL_NATIVE_STREAMING_SUMMARY .*mode=historical-whole .*visited_nodes=1302 .*terminal_nodes=661 .*rejected_leaves=0 ' \
  "$output_dir/whole-stream-results.txt"

awk '
  function value(name, i, field) {
    for (i=1; i<=NF; ++i) {
      split($i,field,"="); if(field[1]==name)return field[2]
    }
  }
  FILENAME==ARGV[1] {
    idx=value("index"); upper=value("upper")
    baseline[idx]=(substr(upper,1,1)=="-"); next
  }
  FILENAME==ARGV[2] {
    idx=value("index"); upper=value("upper")
    candidate=(substr(upper,1,1)=="-")
    baseline_negative+=baseline[idx]
    candidate_negative+=candidate
    if (baseline[idx] && !candidate) lost++
    if (!baseline[idx] && candidate) gained++
  }
  END {
    print "baseline_negative\tcandidate_negative\tlost\tgained"
    printf "%d\t%d\t%d\t%d\n",baseline_negative,candidate_negative,lost+0,gained+0
    if (baseline_negative != 682 || candidate_negative != 703 || lost != 0 || gained != 21) exit 1
  }
' "$output_dir/baseline-bounds.txt" "$output_dir/whole-bounds.txt" \
  >"$output_dir/pruning-preservation.tsv"

"$analyzer" "$output_dir/baseline-bounds.txt" \
  "$output_dir/whole-bounds.txt" >"$output_dir/whole-vs-baseline-bounds.json"

awk '
  function value(name, i, field) { for(i=1;i<=NF;++i){split($i,field,"=");if(field[1]==name)return field[2]} }
  {lane=value("lane");if(lane=="")next;count[lane]++;preparation[lane]+=value("preparation_seconds");evaluation[lane]+=value("evaluation_seconds")}
  END {
    print "lane\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds"
    for(i=1;i<=2;++i){lane=(i==1?"baseline":"whole");p=preparation[lane]/count[lane];e=evaluation[lane]/count[lane];printf "%s\t%d\t%.9f\t%.9f\t%.9f\n",lane,count[lane],p,e,p+e}
    bp=preparation["baseline"]/count["baseline"];be=evaluation["baseline"]/count["baseline"]
    wp=preparation["whole"]/count["whole"];we=evaluation["whole"]/count["whole"]
    printf "whole_speedup\t%d\t0\t%.9f\t%.9f\n",count["whole"],be/we,(bp+be)/(wp+we)
  }
' "$batch_summaries" >"$output_dir/batch-times.tsv"

awk '
  function value(name, i, field) { for(i=1;i<=NF;++i){split($i,field,"=");if(field[1]==name)return field[2]} }
  {lane=value("lane");if(lane=="")next;count[lane]++;input[lane]+=value("input_seconds");preparation[lane]+=value("reusable_preparation_seconds");traversal[lane]+=value("traversal_seconds");total[lane]+=value("total_seconds")}
  END {
    print "lane\truns\tmean_input_seconds\tmean_reusable_preparation_seconds\tmean_traversal_seconds\tmean_total_seconds"
    for(i=1;i<=2;++i){lane=(i==1?"baseline":"whole");printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.9f\n",lane,count[lane],input[lane]/count[lane],preparation[lane]/count[lane],traversal[lane]/count[lane],total[lane]/count[lane]}
    bt=traversal["baseline"]/count["baseline"];wt=traversal["whole"]/count["whole"]
    ba=total["baseline"]/count["baseline"];wa=total["whole"]/count["whole"]
    printf "whole_speedup\t%d\t0\t0\t%.9f\t%.9f\n",count["whole"],bt/wt,ba/wa
  }
' "$stream_summaries" >"$output_dir/stream-times.tsv"

awk -v begin="$build_begin" -v batch="$build_batch_end" \
  -v stream="$build_stream_end" 'BEGIN { print "phase\tseconds"; printf "build_batch\t%.9f\n",(batch-begin)/1e9; printf "build_streaming\t%.9f\n",(stream-batch)/1e9 }' \
  >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$base_source" "$stream_source" "$program" \
  "$historical_jobs" "$expected" "$full_jobs" "$topology" \
  "$output_dir/source-revision.txt" "$output_dir"/*-summaries.txt \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir"/*-decisions.txt "$output_dir"/*-times.tsv \
  "$output_dir/pruning-preservation.tsv" \
  "$output_dir/whole-vs-baseline-bounds.json" \
  "$output_dir/one-time-costs.tsv" "$output_dir"/*-resource.txt \
  >"$output_dir/evidence.sha256"

cat "$output_dir/batch-times.tsv"
cat "$output_dir/stream-times.tsv"
cat "$output_dir/pruning-preservation.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_WHOLE_BOX_JET_OK DEVELOPMENT_NON_RELEASE'
