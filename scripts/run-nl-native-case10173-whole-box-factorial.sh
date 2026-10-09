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
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
source_revision=${CANDLE_NL_NATIVE_SOURCE_REVISION:-HEAD}
source_path=tools/nl_native_fixed_scale_case10173.cc
analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$jobs" "$expected"; do [[ -f "$input" ]]; done
[[ -x "$analyzer" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]
[[ $(sha256sum "$program" | cut -d' ' -f1) == \
   b044687f3c3f77b50d8dfd7afd8ebb9c7af1fb30637acc2b629107cee6e67b01 ]]
[[ $(sha256sum "$jobs" | cut -d' ' -f1) == \
   c03587283858e7ed3f60ba90909e542a7186707a0f45f702249af57e73920afb ]]
[[ $(sha256sum "$expected" | cut -d' ' -f1) == \
   0bd62feaccadf637b599b8a8531cf825a766351249238cd01ab4bf5ee0ec1d9a ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

resolved_revision=$(git -C "$repo_root" rev-parse "$source_revision^{commit}")
source_file="$output_dir/nl_native_fixed_scale_case10173.cc"
git -C "$repo_root" show "$resolved_revision:$source_path" >"$source_file"
printf 'revision=%s\nsource_path=%s\n' "$resolved_revision" "$source_path" \
  >"$output_dir/source-revision.txt"
rg -q 'whole-box case10173 historical source/slot drift' "$source_file"

common_build=(-std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include")
build_begin=$(date +%s%N)
g++ "${common_build[@]}" -DCANDLE_NL_FIXED_INT128=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-exact"
build_exact_end=$(date +%s%N)
g++ "${common_build[@]}" -DCANDLE_NL_FIXED_DOUBLE=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-padded"
build_padded_end=$(date +%s%N)

common_options=(
  --binary-scale-bits=23
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --source-dag-cache
  --computed-tight-sqrt-certificates
  --taylor-reconstructed-box
  --whole-box-jet
  --sign-specialized-interval-products
  --allow-rejected-development
  --count-fixed-quotients
)

lane_binary() {
  [[ "$1" == *-exact ]] && \
    printf '%s\n' "$output_dir/nl-native-exact" || \
    printf '%s\n' "$output_dir/nl-native-padded"
}

lane_options() {
  local lane=$1
  [[ "$lane" == *-exact ]] && \
    printf '%s\0' --dyadic-shift-fixed-quotient
  [[ "$lane" == *-padded ]] && \
    printf '%s\0' --subdivide-representation-failures-development
  [[ "$lane" == historical-* ]] && printf '%s\0' \
    --historical-dihedral --historical-block-rounding \
    --historical-center-tangent
}

run_summary() {
  local lane=$1 repetition=$2 destination=$3 binary
  local -a options=("${common_options[@]}") lane_specific
  binary=$(lane_binary "$lane")
  mapfile -d '' -t lane_specific < <(lane_options "$lane")
  options+=("${lane_specific[@]}")
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY ' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(generic-exact generic-padded historical-exact historical-padded)
summaries="$output_dir/summaries.txt"
: >"$summaries"
for lane in "${lanes[@]}"; do run_summary "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_summary "$lane" "$repetition" "$summaries"
  done
done

for lane in "${lanes[@]}"; do
  binary=$(lane_binary "$lane")
  options=("${common_options[@]}")
  mapfile -d '' -t lane_specific < <(lane_options "$lane")
  options+=("${lane_specific[@]}")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-resource.txt" \
    "$binary" "$program" "$jobs" "$expected" "${options[@]}" \
    >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT ' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
done

for lane in historical-exact historical-padded; do
  rg -q "^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=4173 .*whole_box_jet=1 .*case_id=10173 .*representation_failure_subdivisions=0 .*accepted=4173 " \
    "$output_dir/$lane-results.txt"
done

compare_decisions() {
  local exact_file=$1 padded_file=$2 destination=$3
  awk '
    function value(name,i,field){for(i=1;i<=NF;++i){split($i,field,"=");if(field[1]==name)return field[2]}}
    FILENAME==ARGV[1]{idx=value("index");upper=value("upper");exact[idx]=(substr(upper,1,1)=="-");next}
    FILENAME==ARGV[2]{idx=value("index");upper=value("upper");padded=(substr(upper,1,1)=="-");exact_negative+=exact[idx];padded_negative+=padded;if(exact[idx]&&!padded)lost++;if(!exact[idx]&&padded)gained++}
    END{print "exact_negative\tpadded_negative\tlost\tgained";printf "%d\t%d\t%d\t%d\n",exact_negative,padded_negative,lost+0,gained+0}
  ' "$exact_file" "$padded_file" >"$destination"
}

compare_decisions "$output_dir/generic-exact-bounds.txt" \
  "$output_dir/generic-padded-bounds.txt" \
  "$output_dir/generic-decision-preservation.tsv"
compare_decisions "$output_dir/historical-exact-bounds.txt" \
  "$output_dir/historical-padded-bounds.txt" \
  "$output_dir/historical-decision-preservation.tsv"
tail -n 1 "$output_dir/historical-decision-preservation.tsv" | \
  rg -q $'^4173\t4173\t0\t0$'

"$analyzer" "$output_dir/generic-exact-bounds.txt" \
  "$output_dir/generic-padded-bounds.txt" \
  >"$output_dir/generic-padded-vs-exact.json"
"$analyzer" "$output_dir/historical-exact-bounds.txt" \
  "$output_dir/historical-padded-bounds.txt" \
  >"$output_dir/historical-padded-vs-exact.json"
"$analyzer" "$output_dir/generic-exact-bounds.txt" \
  "$output_dir/historical-exact-bounds.txt" \
  >"$output_dir/historical-vs-generic-exact.json"
"$analyzer" "$output_dir/generic-padded-bounds.txt" \
  "$output_dir/historical-padded-bounds.txt" \
  >"$output_dir/historical-vs-generic-padded.json"

awk '
  function value(name,i,field){for(i=1;i<=NF;++i){split($i,field,"=");if(field[1]==name)return field[2]}}
  {lane=value("lane");if(lane=="")next;current=value("accepted");count[lane]++;preparation[lane]+=value("preparation_seconds");evaluation[lane]+=value("evaluation_seconds");if(count[lane]==1||current<minimum[lane])minimum[lane]=current}
  END{print "lane\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";for(i=1;i<=4;++i){lane=(i==1?"generic-exact":i==2?"generic-padded":i==3?"historical-exact":"historical-padded");p=preparation[lane]/count[lane];e=evaluation[lane]/count[lane];printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n",lane,count[lane],p,e,p+e,minimum[lane]}ge=evaluation["generic-exact"]/count["generic-exact"];gp=evaluation["generic-padded"]/count["generic-padded"];he=evaluation["historical-exact"]/count["historical-exact"];hp=evaluation["historical-padded"]/count["historical-padded"];printf "generic_padded_speedup\t%d\t0\t%.9f\t0\t0\n",count["generic-padded"],ge/gp;printf "historical_padded_speedup\t%d\t0\t%.9f\t0\t0\n",count["historical-padded"],he/hp;printf "historical_over_generic_exact\t%d\t0\t%.9f\t0\t0\n",count["historical-exact"],ge/he;printf "historical_over_generic_padded\t%d\t0\t%.9f\t0\t0\n",count["historical-padded"],gp/hp}
' "$summaries" >"$output_dir/times.tsv"

awk -v begin="$build_begin" -v exact="$build_exact_end" \
  -v padded="$build_padded_end" 'BEGIN{print "phase\tseconds";printf "build_exact\t%.9f\n",(exact-begin)/1e9;printf "build_padded\t%.9f\n",(padded-exact)/1e9}' \
  >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/source-revision.txt" "$summaries" \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir"/*-resource.txt "$output_dir"/*-preservation.tsv \
  "$output_dir"/*.json "$output_dir/times.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/evidence.sha256"

cat "$output_dir/times.tsv"
cat "$output_dir/generic-decision-preservation.tsv"
cat "$output_dir/historical-decision-preservation.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_WHOLE_BOX_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
