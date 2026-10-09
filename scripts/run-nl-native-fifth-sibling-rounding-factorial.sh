#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  printf 'usage: %s PROGRAM.cval HISTORICAL-JOBS.tsv EXPECTED.tsv OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
expected=$3
output_dir=$4
repetitions=$5
analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
source_revision=${CANDLE_NL_NATIVE_SOURCE_REVISION:-HEAD}
source_path=tools/nl_native_fixed_scale_case10173.cc

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$jobs" "$expected"; do [[ -f "$input" ]]; done
[[ -x "$analyzer" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq 1344 ]]
[[ $(wc -l <"$expected") -eq 1344 ]]
[[ $(sha256sum "$program" | cut -d' ' -f1) == \
   82f5c7f81b7a6ec292b6426caddaddb1ce7fde5dfbd83c2900a072f679a28dcb ]]
[[ $(sha256sum "$jobs" | cut -d' ' -f1) == \
   aee9627da2ca282eb8f32289c2c47d79da99afc517ea883ce8f59566ab660f2a ]]
[[ $(sha256sum "$expected" | cut -d' ' -f1) == \
   553aacdb3ee8ab4d407eecb8517d59b80791828fc086ecaa16bfde7af9e8b324 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

resolved_source_revision=$(git -C "$repo_root" rev-parse "$source_revision^{commit}")
source_file="$output_dir/nl_native_fixed_scale_case10173.cc"
git -C "$repo_root" show "$resolved_source_revision:$source_path" >"$source_file"
printf 'revision=%s\npath=%s\n' "$resolved_source_revision" "$source_path" \
  >"$output_dir/source-revision.txt"
rg -q -- '--unsafe-unrounded-hardware' "$source_file"
rg -q -- '--specialized-delta-historical-dihedrals' "$source_file"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_FIXED_DOUBLE=1 -DCANDLE_NL_CASE_ID=16594 \
  -DCANDLE_NL_SQRT_SLOTS=10 -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-double"
build_end=$(date +%s%N)

lane_options() {
  local lane=$1
  printf '%s\0' --count-fixed-quotients --binary-scale-bits=40 \
    --sign-specialized-interval-products --fixed-sqrt-inverse-kernels \
    --fixed-atan-kernel --taylor-reconstructed-box \
    --specialized-delta-radicands --specialized-delta-derivatives \
    --prepared-simple-polynomials --source-dag-cache \
    --computed-tight-sqrt-certificates --allow-rejected-development \
    --subdivide-domain-failures-development \
    --subdivide-representation-failures-development \
    --specialized-delta-historical-dihedrals
  [[ "$lane" == unrounded ]] && printf '%s\0' --unsafe-unrounded-hardware
}

run_lane() {
  local lane=$1 repetition=$2 destination=$3
  local -a options
  mapfile -d '' -t options < <(lane_options "$lane")
  "$output_dir/nl-native-double" "$program" "$jobs" "$expected" \
    "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane padded warmup /dev/null
run_lane unrounded warmup /dev/null
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then lanes=(padded unrounded); else lanes=(unrounded padded); fi
  for lane in "${lanes[@]}"; do run_lane "$lane" "$repetition" "$summaries"; done
done

for lane in padded unrounded; do
  mapfile -d '' -t options < <(lane_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-resource.txt" \
    "$output_dir/nl-native-double" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' "$output_dir/$lane-results.txt" \
    >"$output_dir/$lane-bounds.txt"
  [[ $(wc -l <"$output_dir/$lane-bounds.txt") -eq 1344 ]]
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=1344 backend=double-integer .*specialized_delta_historical_dihedrals=1 specialized_delta_dihedral_chain_count=3 .*domain_failure_subdivisions=84 .*accepted=682 ' \
    "$output_dir/$lane-results.txt"
done
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY .*unsafe_unrounded_hardware=0 .*representation_failure_subdivisions=1 ' \
  "$output_dir/padded-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY .*unsafe_unrounded_hardware=1 .*representation_failure_subdivisions=0 ' \
  "$output_dir/unrounded-results.txt"

"$analyzer" "$output_dir/padded-results.txt" \
  "$output_dir/unrounded-results.txt" >"$output_dir/unrounded-vs-padded-bounds.json"

awk '
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
    accepted[lane]=value("accepted")
    domains[lane]=value("domain_failure_subdivisions")
  }
  END {
    print "lane\truns\taccepted\tdomain_subdivisions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds"
    names[1]="padded"; names[2]="unrounded"
    for (i=1; i<=2; ++i) {
      lane=names[i]; p=preparation[lane]/count[lane]
      e=evaluation[lane]/count[lane]
      printf "%s\t%d\t%d\t%d\t%.9f\t%.9f\t%.9f\n",lane,count[lane],accepted[lane],domains[lane],p,e,p+e
    }
    pp=preparation["padded"]/count["padded"]
    pe=evaluation["padded"]/count["padded"]
    up=preparation["unrounded"]/count["unrounded"]
    ue=evaluation["unrounded"]/count["unrounded"]
    printf "unrounded_speedup\t%d\t%d\t%d\t0\t%.9f\t%.9f\n",count["padded"],accepted["unrounded"],domains["unrounded"],pe/ue,(pp+pe)/(up+ue)
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v end="$build_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_double\t%.9f\n",(end-begin)/1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$analyzer" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/source-revision.txt" "$output_dir/summaries.txt" \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir/unrounded-vs-padded-bounds.json" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  "$output_dir"/*-resource.txt >"$output_dir/evidence.sha256"

cat "$output_dir/phase-times.tsv"
cat "$output_dir/unrounded-vs-padded-bounds.json"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_ROUNDING_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
