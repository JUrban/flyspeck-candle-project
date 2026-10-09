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
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

resolved_source_revision=$(git -C "$repo_root" rev-parse "$source_revision^{commit}")
source_file="$output_dir/nl_native_fixed_scale_case10173.cc"
git -C "$repo_root" show "$resolved_source_revision:$source_path" >"$source_file"
printf 'revision=%s\npath=%s\n' "$resolved_source_revision" "$source_path" \
  >"$output_dir/source-revision.txt"
rg -q -- '--source-dag-cache' "$source_file"
rg -q -- '--specialized-delta-historical-dihedrals' "$source_file"
rg -q 'historical_delta_dihedral' "$source_file"

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
    --allow-rejected-development --subdivide-domain-failures-development
  [[ "$lane" == historical ]] && \
    printf '%s\0' --specialized-delta-historical-dihedrals
}

run_summary() {
  local lane=$1 repetition=$2 destination=$3
  local -a options
  mapfile -d '' -t options < <(lane_options "$lane")
  "$output_dir/nl-native-exact" "$program" "$jobs" "$expected" \
    "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_summary dag warmup /dev/null
run_summary historical warmup /dev/null
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then lanes=(dag historical); else lanes=(historical dag); fi
  for lane in "${lanes[@]}"; do
    run_summary "$lane" "$repetition" "$summaries"
  done
done

for lane in dag historical; do
  mapfile -d '' -t options < <(lane_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-resource.txt" \
    "$output_dir/nl-native-exact" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  for profile in timing rounding; do
    profile_option=--profile
    [[ "$profile" == rounding ]] && profile_option=--rounding-profile
    /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
      -o "$output_dir/$lane-$profile-resource.txt" \
      "$output_dir/nl-native-exact" "$program" "$jobs" "$expected" \
      "${options[@]}" "$profile_option" \
      >"$output_dir/$lane-$profile-results.txt"
    rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_OK DEVELOPMENT_NON_RELEASE case=16594 cells=1344$' \
      "$output_dir/$lane-$profile-results.txt"
  done
done

rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=1344 .*specialized_delta_historical_dihedrals=0 .*accepted=7 ' \
  "$output_dir/dag-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=1344 .*specialized_delta_historical_dihedrals=1 specialized_delta_dihedral_chain_count=3 .*accepted=682 ' \
  "$output_dir/historical-results.txt"
[[ $(rg -c '^CANDLE_NL_NATIVE_FIXED_SCALE_PROFILE ' \
     "$output_dir/dag-timing-results.txt") -eq 167 ]]
[[ $(rg -c '^CANDLE_NL_NATIVE_FIXED_SCALE_PROFILE ' \
     "$output_dir/historical-timing-results.txt") -eq 167 ]]
timing_historical_observations=$(awk '
  /^CANDLE_NL_NATIVE_FIXED_SCALE_PROFILE / &&
      / label=historical_delta_dihedral / {
    for (i=1; i<=NF; ++i) {
      split($i, field, "=")
      if (field[1] == "observations") total+=field[2]
    }
  }
  END { print total+0 }
' "$output_dir/historical-timing-results.txt")
rounding_historical_observations=$(awk '
  /^CANDLE_NL_NATIVE_FIXED_SCALE_ROUNDING_PROFILE / &&
      / label=historical_delta_dihedral / {
    for (i=1; i<=NF; ++i) {
      split($i, field, "=")
      if (field[1] == "observations") total+=field[2]
    }
  }
  END { print total+0 }
' "$output_dir/historical-rounding-results.txt")
[[ "$timing_historical_observations" -eq 3780 ]]
[[ "$rounding_historical_observations" -eq 3864 ]]

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
  }
  END {
    print "lane\truns\taccepted\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds"
    names[1]="dag"; names[2]="historical"
    for (i=1; i<=2; ++i) {
      lane=names[i]; p=preparation[lane]/count[lane]
      e=evaluation[lane]/count[lane]
      printf "%s\t%d\t%d\t%.9f\t%.9f\t%.9f\n",lane,count[lane],accepted[lane],p,e,p+e
    }
    dp=preparation["dag"]/count["dag"]
    de=evaluation["dag"]/count["dag"]
    hp=preparation["historical"]/count["historical"]
    he=evaluation["historical"]/count["historical"]
    printf "historical_over_dag_fixed_box_ratio\t%d\t%d\t0\t%.9f\t%.9f\n",count["dag"],accepted["historical"],he/de,(hp+he)/(dp+de)
  }
' "$summaries" >"$output_dir/phase-times.tsv"

printf 'lane\tkind\tlabel\tobservations\tnanoseconds\tfloor_quotients\tceil_quotients\ttotal_quotients\n' \
  >"$output_dir/profile-attribution.tsv"
profile_rows="$output_dir/profile-attribution.rows"
: >"$profile_rows"
for lane in dag historical; do
  awk -v lane="$lane" '
    /^CANDLE_NL_NATIVE_FIXED_SCALE_PROFILE / {
      label=""; observations=0; nanoseconds=0
      for (i=1; i<=NF; ++i) {
        split($i, field, "=")
        if (field[1] == "label") label=field[2]
        if (field[1] == "observations") observations=field[2]
        if (field[1] == "nanoseconds") nanoseconds=field[2]
      }
      key=label; count[key]+=observations; elapsed[key]+=nanoseconds
    }
    END {
      for (key in count) printf "%s\ttiming\t%s\t%d\t%d\t0\t0\t0\n",lane,key,count[key],elapsed[key]
    }
  ' "$output_dir/$lane-timing-results.txt" >>"$profile_rows"
  awk -v lane="$lane" '
    /^CANDLE_NL_NATIVE_FIXED_SCALE_ROUNDING_PROFILE / {
      label=""; observations=0; nanoseconds=0; floor=0; ceil=0; total=0
      for (i=1; i<=NF; ++i) {
        split($i, field, "=")
        if (field[1] == "label") label=field[2]
        if (field[1] == "observations") observations=field[2]
        if (field[1] == "nanoseconds") nanoseconds=field[2]
        if (field[1] == "floor_quotients") floor=field[2]
        if (field[1] == "ceil_quotients") ceil=field[2]
        if (field[1] == "total_quotients") total=field[2]
      }
      key=label; count[key]+=observations; elapsed[key]+=nanoseconds
      floors[key]+=floor; ceils[key]+=ceil; totals[key]+=total
    }
    END {
      for (key in count) printf "%s\trounding\t%s\t%d\t%d\t%d\t%d\t%d\n",lane,key,count[key],elapsed[key],floors[key],ceils[key],totals[key]
    }
  ' "$output_dir/$lane-rounding-results.txt" >>"$profile_rows"
done
sort -t $'\t' -k1,1 -k2,2 -k3,3 "$profile_rows" \
  >>"$output_dir/profile-attribution.tsv"
rm "$profile_rows"

awk -v begin="$build_begin" -v end="$build_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_exact\t%.9f\n",(end-begin)/1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/source-revision.txt" "$output_dir/summaries.txt" \
  "$output_dir"/*-results.txt "$output_dir"/*-resource.txt \
  "$output_dir/phase-times.tsv" "$output_dir/profile-attribution.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/evidence.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_HELD_AXIS_PROFILE_OK DEVELOPMENT_NON_RELEASE'
