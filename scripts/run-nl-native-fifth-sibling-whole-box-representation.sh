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
rg -q 'representation_subdivisions' "$stream_source"

common=(-std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include")
shape=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)
build_begin=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_INT128=1 \
  -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 "${shape[@]}" "$base_source" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-batch-exact"
build_exact_batch_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_DOUBLE=1 "${shape[@]}" \
  "$base_source" -lgmpxx -lgmp -o "$output_dir/nl-native-batch-padded"
build_padded_batch_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_INT128=1 \
  -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 "${shape[@]}" "$stream_source" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-stream-exact"
build_exact_stream_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_DOUBLE=1 "${shape[@]}" \
  "$stream_source" -lgmpxx -lgmp -o "$output_dir/nl-native-stream-padded"
build_padded_stream_end=$(date +%s%N)

batch_binary() {
  [[ "$1" == exact ]] && printf '%s\n' "$output_dir/nl-native-batch-exact" || \
    printf '%s\n' "$output_dir/nl-native-batch-padded"
}

stream_binary() {
  [[ "$1" == exact ]] && printf '%s\n' "$output_dir/nl-native-stream-exact" || \
    printf '%s\n' "$output_dir/nl-native-stream-padded"
}

batch_options() {
  local lane=$1
  printf '%s\0' --count-fixed-quotients --binary-scale-bits=40 \
    --sign-specialized-interval-products --fixed-sqrt-inverse-kernels \
    --fixed-atan-kernel --taylor-reconstructed-box \
    --specialized-delta-radicands --specialized-delta-derivatives \
    --prepared-simple-polynomials --source-dag-cache \
    --computed-tight-sqrt-certificates --allow-rejected-development \
    --subdivide-domain-failures-development \
    --specialized-delta-historical-dihedrals --whole-box-jet
  [[ "$lane" == exact ]] && printf '%s\0' --dyadic-shift-fixed-quotient
  [[ "$lane" == padded ]] && \
    printf '%s\0' --subdivide-representation-failures-development
}

run_batch_summary() {
  local lane=$1 repetition=$2 destination=$3 binary
  local -a options
  binary=$(batch_binary "$lane")
  mapfile -d '' -t options < <(batch_options "$lane")
  "$binary" "$program" "$historical_jobs" "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY ' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

run_stream_summary() {
  local lane=$1 repetition=$2 destination=$3 binary
  binary=$(stream_binary "$lane")
  "$binary" "$program" "$full_jobs" "$topology" historical-whole |
    rg '^CANDLE_NL_NATIVE_STREAMING_SUMMARY ' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

batch_summaries="$output_dir/batch-summaries.txt"
stream_summaries="$output_dir/stream-summaries.txt"
: >"$batch_summaries"
: >"$stream_summaries"
for lane in exact padded; do
  run_batch_summary "$lane" warmup /dev/null
  run_stream_summary "$lane" warmup /dev/null
done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then lanes=(exact padded); else lanes=(padded exact); fi
  for lane in "${lanes[@]}"; do
    run_batch_summary "$lane" "$repetition" "$batch_summaries"
    run_stream_summary "$lane" "$repetition" "$stream_summaries"
  done
done

for lane in exact padded; do
  binary=$(batch_binary "$lane")
  mapfile -d '' -t options < <(batch_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-batch-resource.txt" \
    "$binary" "$program" "$historical_jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-batch-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT ' \
    "$output_dir/$lane-batch-results.txt" >"$output_dir/$lane-bounds.txt"

  binary=$(stream_binary "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-stream-resource.txt" \
    "$binary" "$program" "$full_jobs" "$topology" historical-whole \
    >"$output_dir/$lane-stream-results.txt"
  rg '^CANDLE_NL_NATIVE_STREAMING_RESULT ' \
    "$output_dir/$lane-stream-results.txt" >"$output_dir/$lane-stream-decisions.txt"
done

rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=1344 backend=mixed-native-int128-checked-int192 .*whole_box_jet=1 .*domain_failure_subdivisions=84 representation_failure_subdivisions=0 .*accepted=703 ' \
  "$output_dir/exact-batch-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=1344 backend=double-integer .*whole_box_jet=1 .*domain_failure_subdivisions=84 representation_failure_subdivisions=1 .*accepted=703 ' \
  "$output_dir/padded-batch-results.txt"
for lane in exact padded; do
  representation=0
  [[ "$lane" == padded ]] && representation=1
  rg -q "^CANDLE_NL_NATIVE_STREAMING_SUMMARY .*visited_nodes=1302 .*terminal_nodes=661 .*rejected_leaves=0 .*domain_subdivisions=84 representation_subdivisions=$representation .*maximum_depth=13 " \
    "$output_dir/$lane-stream-results.txt"
done

awk '
  function value(name,i,field){for(i=1;i<=NF;++i){split($i,field,"=");if(field[1]==name)return field[2]}}
  FILENAME==ARGV[1]{idx=value("index");upper=value("upper");exact[idx]=(substr(upper,1,1)=="-");next}
  FILENAME==ARGV[2]{idx=value("index");upper=value("upper");padded=(substr(upper,1,1)=="-");exact_negative+=exact[idx];padded_negative+=padded;if(exact[idx]&&!padded)lost++;if(!exact[idx]&&padded)gained++}
  END{print "exact_negative\tpadded_negative\tlost\tgained";printf "%d\t%d\t%d\t%d\n",exact_negative,padded_negative,lost+0,gained+0;if(exact_negative!=703||padded_negative!=703||lost!=0||gained!=0)exit 1}
' "$output_dir/exact-bounds.txt" "$output_dir/padded-bounds.txt" \
  >"$output_dir/pruning-preservation.tsv"

"$analyzer" "$output_dir/exact-bounds.txt" "$output_dir/padded-bounds.txt" \
  >"$output_dir/padded-vs-exact-bounds.json"

awk '
  function value(name,i,field){for(i=1;i<=NF;++i){split($i,field,"=");if(field[1]==name)return field[2]}}
  {lane=value("lane");if(lane=="")next;count[lane]++;preparation[lane]+=value("preparation_seconds");evaluation[lane]+=value("evaluation_seconds")}
  END{print "lane\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds";for(i=1;i<=2;++i){lane=(i==1?"exact":"padded");p=preparation[lane]/count[lane];e=evaluation[lane]/count[lane];printf "%s\t%d\t%.9f\t%.9f\t%.9f\n",lane,count[lane],p,e,p+e}ep=preparation["exact"]/count["exact"];ee=evaluation["exact"]/count["exact"];pp=preparation["padded"]/count["padded"];pe=evaluation["padded"]/count["padded"];printf "padded_speedup\t%d\t0\t%.9f\t%.9f\n",count["padded"],ee/pe,(ep+ee)/(pp+pe)}
' "$batch_summaries" >"$output_dir/batch-times.tsv"

awk '
  function value(name,i,field){for(i=1;i<=NF;++i){split($i,field,"=");if(field[1]==name)return field[2]}}
  {lane=value("lane");if(lane=="")next;count[lane]++;input[lane]+=value("input_seconds");preparation[lane]+=value("reusable_preparation_seconds");traversal[lane]+=value("traversal_seconds");total[lane]+=value("total_seconds")}
  END{print "lane\truns\tmean_input_seconds\tmean_reusable_preparation_seconds\tmean_traversal_seconds\tmean_total_seconds";for(i=1;i<=2;++i){lane=(i==1?"exact":"padded");printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.9f\n",lane,count[lane],input[lane]/count[lane],preparation[lane]/count[lane],traversal[lane]/count[lane],total[lane]/count[lane]}et=traversal["exact"]/count["exact"];pt=traversal["padded"]/count["padded"];ea=total["exact"]/count["exact"];pa=total["padded"]/count["padded"];printf "padded_speedup\t%d\t0\t0\t%.9f\t%.9f\n",count["padded"],et/pt,ea/pa}
' "$stream_summaries" >"$output_dir/stream-times.tsv"

awk -v begin="$build_begin" -v eb="$build_exact_batch_end" \
  -v pb="$build_padded_batch_end" -v es="$build_exact_stream_end" \
  -v ps="$build_padded_stream_end" 'BEGIN{print "phase\tseconds";printf "build_exact_batch\t%.9f\n",(eb-begin)/1e9;printf "build_padded_batch\t%.9f\n",(pb-eb)/1e9;printf "build_exact_stream\t%.9f\n",(es-pb)/1e9;printf "build_padded_stream\t%.9f\n",(ps-es)/1e9}' \
  >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$base_source" "$stream_source" "$program" \
  "$historical_jobs" "$expected" "$full_jobs" "$topology" \
  "$output_dir/source-revision.txt" "$output_dir"/*-summaries.txt \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir"/*-decisions.txt "$output_dir"/*-times.tsv \
  "$output_dir/pruning-preservation.tsv" \
  "$output_dir/padded-vs-exact-bounds.json" \
  "$output_dir/one-time-costs.tsv" "$output_dir"/*-resource.txt \
  >"$output_dir/evidence.sha256"

cat "$output_dir/batch-times.tsv"
cat "$output_dir/stream-times.tsv"
cat "$output_dir/pruning-preservation.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_WHOLE_BOX_REPRESENTATION_OK DEVELOPMENT_NON_RELEASE'
