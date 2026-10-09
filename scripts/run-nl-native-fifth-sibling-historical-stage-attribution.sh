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

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$jobs" "$expected"; do [[ -f "$input" ]]; done
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
rg -q -- '--historical-stage-profile' "$source_file"
rg -q 'CANDLE_NL_NATIVE_FIXED_SCALE_HISTORICAL_PROFILE' "$source_file"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_FIXED_INT128=1 -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 \
  -DCANDLE_NL_CASE_ID=16594 -DCANDLE_NL_SQRT_SLOTS=10 \
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-exact"
build_end=$(date +%s%N)

lane_options() {
  local lane=$1
  printf '%s\0' --count-fixed-quotients --binary-scale-bits=40 \
    --dyadic-shift-fixed-quotient --sign-specialized-interval-products \
    --fixed-sqrt-inverse-kernels --fixed-atan-kernel \
    --taylor-reconstructed-box --specialized-delta-radicands \
    --specialized-delta-derivatives --prepared-simple-polynomials \
    --source-dag-cache --computed-tight-sqrt-certificates \
    --allow-rejected-development --subdivide-domain-failures-development \
    --specialized-delta-historical-dihedrals
  [[ "$lane" == profiled ]] && printf '%s\0' --historical-stage-profile
}

run_lane() {
  local lane=$1 destination=$2
  local -a options
  mapfile -d '' -t options < <(lane_options "$lane")
  "$output_dir/nl-native-exact" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$destination"
}

run_lane baseline /dev/null
run_lane profiled /dev/null
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    lanes=(baseline profiled)
  else
    lanes=(profiled baseline)
  fi
  for lane in "${lanes[@]}"; do
    run_lane "$lane" "$output_dir/repetition-$repetition-$lane.txt"
  done
done

summaries="$output_dir/summaries.txt"
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  for lane in baseline profiled; do
    result="$output_dir/repetition-$repetition-$lane.txt"
    rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_OK DEVELOPMENT_NON_RELEASE case=16594 cells=1344$' \
      "$result"
    rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=1344 .*specialized_delta_historical_dihedrals=1 specialized_delta_dihedral_chain_count=3 .*domain_failure_subdivisions=84 .*accepted=682 ' \
      "$result"
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY ' "$result" |
      sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
  done
  [[ $(rg -c '^CANDLE_NL_NATIVE_FIXED_SCALE_HISTORICAL_PROFILE ' \
      "$output_dir/repetition-$repetition-profiled.txt") -eq 15 ]]
done

rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT ' \
  "$output_dir/repetition-1-baseline.txt" >"$output_dir/baseline-bounds.txt"
rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT ' \
  "$output_dir/repetition-1-profiled.txt" >"$output_dir/profiled-bounds.txt"
cmp "$output_dir/baseline-bounds.txt" "$output_dir/profiled-bounds.txt"
[[ $(sha256sum "$output_dir/baseline-bounds.txt" | cut -d' ' -f1) == \
   9b34fe45f56c6d50bbac6d33bc0f6cf007df5ee2d5d43815c904b2ff40da5aa5 ]]

awk '
  function value(name, i, field) {
    for (i=1; i<=NF; ++i) {
      split($i, field, "="); if (field[1] == name) return field[2]
    }
  }
  {
    lane=value("lane"); if (lane == "") next
    count[lane]++
    preparation[lane]+=value("preparation_seconds")
    evaluation[lane]+=value("evaluation_seconds")
    accepted[lane]=value("accepted")
  }
  END {
    print "lane\truns\taccepted\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds"
    names[1]="baseline"; names[2]="profiled"
    for (i=1; i<=2; ++i) {
      lane=names[i]
      p=preparation[lane]/count[lane]; e=evaluation[lane]/count[lane]
      printf "%s\t%d\t%d\t%.9f\t%.9f\t%.9f\n",lane,count[lane],accepted[lane],p,e,p+e
    }
    bp=preparation["baseline"]/count["baseline"]
    be=evaluation["baseline"]/count["baseline"]
    pp=preparation["profiled"]/count["profiled"]
    pe=evaluation["profiled"]/count["profiled"]
    printf "profile_overhead_ratio\t%d\t%d\t0\t%.9f\t%.9f\n",count["profiled"],accepted["profiled"],pe/be,(pp+pe)/(bp+be)
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk '
  function value(name, i, field) {
    for (i=1; i<=NF; ++i) {
      split($i, field, "="); if (field[1] == name) return field[2]
    }
  }
  /^CANDLE_NL_NATIVE_FIXED_SCALE_HISTORICAL_PROFILE / {
    idx=value("index"); label[idx]=value("label"); runs[idx]++
    observations[idx]+=value("observations")
    nanoseconds[idx]+=value("nanoseconds")
    floor[idx]+=value("floor_quotients")
    ceil[idx]+=value("ceil_quotients")
    products[idx]+=value("interval_products")
    endpoints[idx]+=value("interval_endpoint_products")
    sqrt[idx]+=value("sqrt_steps")
    inverse[idx]+=value("inverse_steps")
    atan[idx]+=value("atan_steps")
  }
  END {
    print "index\tlabel\truns\tmean_observations\tmean_nanoseconds\tstage_share\tmean_floor_quotients\tmean_ceil_quotients\tmean_interval_products\tmean_endpoint_products\tmean_sqrt_steps\tmean_inverse_steps\tmean_atan_steps"
    total=0
    for (idx in nanoseconds) total+=nanoseconds[idx]/runs[idx]
    for (idx=0; idx<15; ++idx) {
      printf "%d\t%s\t%d\t%.3f\t%.3f\t%.9f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\n", \
        idx,label[idx],runs[idx],observations[idx]/runs[idx], \
        nanoseconds[idx]/runs[idx], \
        (nanoseconds[idx]/runs[idx])/total, \
        floor[idx]/runs[idx],ceil[idx]/runs[idx], \
        products[idx]/runs[idx],endpoints[idx]/runs[idx], \
        sqrt[idx]/runs[idx],inverse[idx]/runs[idx], \
        atan[idx]/runs[idx]
    }
  }
' "$output_dir"/repetition-*-profiled.txt \
  >"$output_dir/historical-stage-profile.tsv"

awk -v begin="$build_begin" -v end="$build_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_exact\t%.9f\n",(end-begin)/1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/source-revision.txt" "$output_dir/summaries.txt" \
  "$output_dir"/repetition-*.txt "$output_dir/baseline-bounds.txt" \
  "$output_dir/profiled-bounds.txt" "$output_dir/phase-times.tsv" \
  "$output_dir/historical-stage-profile.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/evidence.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_HISTORICAL_STAGE_ATTRIBUTION_OK DEVELOPMENT_NON_RELEASE'
