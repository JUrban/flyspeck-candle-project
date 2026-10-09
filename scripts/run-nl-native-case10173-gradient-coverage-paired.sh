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
rg -q 'CANDLE_NL_NATIVE_WHOLE_BOX_GRADIENT_PROFILE' "$source_file"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_FIXED_INT128=1 "$source_file" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-exact"
build_end=$(date +%s%N)

common_options=(
  --binary-scale-bits=23
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --source-dag-cache
  --computed-tight-sqrt-certificates
  --taylor-reconstructed-box
  --whole-box-jet
  --whole-box-gradient-profile
  --sign-specialized-interval-products
  --allow-rejected-development
  --count-fixed-quotients
  --dyadic-shift-fixed-quotient
)

lane_options() {
  if [[ "$1" == historical ]]; then
    printf '%s\0' --historical-dihedral --historical-block-rounding \
      --historical-center-tangent
  fi
}

run_lane() {
  local lane=$1 repetition=$2 destination=$3
  local -a options=("${common_options[@]}") lane_specific
  mapfile -d '' -t lane_specific < <(lane_options "$lane")
  options+=("${lane_specific[@]}")
  "$output_dir/nl-native-exact" "$program" "$jobs" "$expected" \
    "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_(WHOLE_BOX_GRADIENT_PROFILE|FIXED_SCALE_SUMMARY) ' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

observations="$output_dir/observations.txt"
: >"$observations"
for lane in generic historical; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if (( repetition % 2 == 1 )); then lanes=(generic historical)
  else lanes=(historical generic)
  fi
  for lane in "${lanes[@]}"; do
    run_lane "$lane" "$repetition" "$observations"
  done
done

for lane in generic historical; do
  options=("${common_options[@]}")
  mapfile -d '' -t lane_specific < <(lane_options "$lane")
  options+=("${lane_specific[@]}")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-resource.txt" \
    "$output_dir/nl-native-exact" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
done

rg -q '^CANDLE_NL_NATIVE_WHOLE_BOX_GRADIENT_PROFILE cells=4173 observations=4173 any_sign_definite=476 all_sign_definite=0 nonnegative_by_coordinate=0,0,0,0,0,0 nonpositive_by_coordinate=0,24,24,0,238,238 zero_by_coordinate=0,0,0,0,0,0 mixed_by_coordinate=4173,4149,4149,4173,3935,3935$' \
  "$output_dir/generic-results.txt"
rg -q '^CANDLE_NL_NATIVE_WHOLE_BOX_GRADIENT_PROFILE cells=4173 observations=4173 any_sign_definite=2342 all_sign_definite=0 nonnegative_by_coordinate=0,147,147,41,0,0 nonpositive_by_coordinate=0,584,597,245,1052,1062 zero_by_coordinate=0,0,0,0,0,0 mixed_by_coordinate=4173,3442,3429,3887,3121,3111$' \
  "$output_dir/historical-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=4173 .*whole_box_gradient_profile=1 .*case_id=10173 .*accepted=96 ' \
  "$output_dir/generic-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=4173 .*whole_box_gradient_profile=1 .*case_id=10173 .*accepted=4173 ' \
  "$output_dir/historical-results.txt"

awk '
  function value(name,i,field){for(i=1;i<=NF;++i){split($i,field,"=");if(field[1]==name)return field[2]}}
  /FIXED_SCALE_SUMMARY/{lane=value("lane");count[lane]++;preparation[lane]+=value("preparation_seconds");evaluation[lane]+=value("evaluation_seconds");accepted[lane]=value("accepted")}
  END{print "lane\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\taccepted";for(i=1;i<=2;++i){lane=(i==1?"generic":"historical");p=preparation[lane]/count[lane];e=evaluation[lane]/count[lane];printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n",lane,count[lane],p,e,p+e,accepted[lane]}g=evaluation["generic"]/count["generic"];h=evaluation["historical"]/count["historical"];printf "historical_evaluation_speedup\t%d\t0\t%.9f\t0\t0\n",count["historical"],g/h}
' "$observations" >"$output_dir/times.tsv"

awk '
  function value(name,i,field){for(i=1;i<=NF;++i){split($i,field,"=");if(field[1]==name)return field[2]}}
  /GRADIENT_PROFILE/{lane=value("lane");if(seen[lane]++)next;any=value("any_sign_definite");printf "%s\t%s\t%.9f\t%s\t%s\n",lane,any,any/4173,value("all_sign_definite"),value("mixed_by_coordinate")}
' "$observations" >"$output_dir/coverage.tsv"
sed -i '1i lane\tboxes_with_sign_definite_coordinate\tfraction\tall_coordinates_sign_definite\tmixed_by_coordinate' \
  "$output_dir/coverage.tsv"

awk -v begin="$build_begin" -v end="$build_end" \
  'BEGIN{print "phase\tseconds";printf "build_exact\t%.9f\n",(end-begin)/1e9}' \
  >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/source-revision.txt" "$observations" \
  "$output_dir"/*-results.txt "$output_dir"/*-resource.txt \
  "$output_dir/times.tsv" "$output_dir/coverage.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/evidence.sha256"

cat "$output_dir/times.tsv"
cat "$output_dir/coverage.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_GRADIENT_COVERAGE_PAIRED_OK DEVELOPMENT_NON_RELEASE'
