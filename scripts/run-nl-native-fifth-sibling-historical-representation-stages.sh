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
rg -q -- '--historical-stage-profile' "$source_file"

common=(-std=c++17 -O2 -Wall -Wextra -Werror)
defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)
build_begin=$(date +%s%N)
g++ "${common[@]}" -I"$boost_include" \
  -DCANDLE_NL_FIXED_INT128=1 -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 \
  "${defines[@]}" "$source_file" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-exact"
build_exact_end=$(date +%s%N)
g++ "${common[@]}" -I"$boost_include" -DCANDLE_NL_FIXED_DOUBLE=1 \
  "${defines[@]}" "$source_file" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-padded"
build_padded_end=$(date +%s%N)

lane_options() {
  local lane=$1
  printf '%s\0' --count-fixed-quotients --binary-scale-bits=40 \
    --sign-specialized-interval-products --fixed-sqrt-inverse-kernels \
    --fixed-atan-kernel --taylor-reconstructed-box \
    --specialized-delta-radicands --specialized-delta-derivatives \
    --prepared-simple-polynomials --source-dag-cache \
    --computed-tight-sqrt-certificates --allow-rejected-development \
    --subdivide-domain-failures-development \
    --specialized-delta-historical-dihedrals
  [[ "$lane" == exact-* ]] && printf '%s\0' --dyadic-shift-fixed-quotient
  [[ "$lane" == padded-* ]] && \
    printf '%s\0' --subdivide-representation-failures-development
  [[ "$lane" == *-profiled ]] && printf '%s\0' --historical-stage-profile
}

lane_binary() {
  case "$1" in
    exact-*) printf '%s\n' "$output_dir/nl-native-exact" ;;
    padded-*) printf '%s\n' "$output_dir/nl-native-padded" ;;
    *) return 1 ;;
  esac
}

run_lane() {
  local lane=$1 destination=$2 binary
  local -a options
  binary=$(lane_binary "$lane")
  mapfile -d '' -t options < <(lane_options "$lane")
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" \
    >"$destination"
}

lanes=(exact-baseline exact-profiled padded-baseline padded-profiled)
for lane in "${lanes[@]}"; do run_lane "$lane" /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$output_dir/repetition-$repetition-$lane.txt"
  done
done

summaries="$output_dir/summaries.txt"
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  for lane in "${lanes[@]}"; do
    result="$output_dir/repetition-$repetition-$lane.txt"
    rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_OK DEVELOPMENT_NON_RELEASE case=16594 cells=1344$' \
      "$result"
    rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=1344 .*specialized_delta_historical_dihedrals=1 specialized_delta_dihedral_chain_count=3 .*domain_failure_subdivisions=84 .*accepted=682 ' \
      "$result"
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY ' "$result" |
      sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
    if [[ "$lane" == *-profiled ]]; then
      [[ $(rg -c '^CANDLE_NL_NATIVE_FIXED_SCALE_HISTORICAL_PROFILE ' \
          "$result") -eq 15 ]]
    fi
  done
done

for representation in exact padded; do
  for mode in baseline profiled; do
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT ' \
      "$output_dir/repetition-1-$representation-$mode.txt" \
      >"$output_dir/$representation-$mode-bounds.txt"
  done
  cmp "$output_dir/$representation-baseline-bounds.txt" \
    "$output_dir/$representation-profiled-bounds.txt"
done
[[ $(sha256sum "$output_dir/exact-baseline-bounds.txt" | cut -d' ' -f1) == \
   9b34fe45f56c6d50bbac6d33bc0f6cf007df5ee2d5d43815c904b2ff40da5aa5 ]]
[[ $(sha256sum "$output_dir/padded-baseline-bounds.txt" | cut -d' ' -f1) == \
   edc44a374c6d637b2f4584054bdcc1c6de89c19937407efc76489be315a56363 ]]

"$analyzer" "$output_dir/exact-baseline-bounds.txt" \
  "$output_dir/padded-baseline-bounds.txt" \
  >"$output_dir/padded-vs-exact-bounds.json"

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
    names[1]="exact-baseline"; names[2]="exact-profiled"
    names[3]="padded-baseline"; names[4]="padded-profiled"
    for (i=1; i<=4; ++i) {
      lane=names[i]; p=preparation[lane]/count[lane]
      e=evaluation[lane]/count[lane]
      printf "%s\t%d\t%d\t%.9f\t%.9f\t%.9f\n",lane,count[lane],accepted[lane],p,e,p+e
    }
    eb=evaluation["exact-baseline"]/count["exact-baseline"]
    ep=evaluation["exact-profiled"]/count["exact-profiled"]
    pb=evaluation["padded-baseline"]/count["padded-baseline"]
    pp=evaluation["padded-profiled"]/count["padded-profiled"]
    ebp=preparation["exact-baseline"]/count["exact-baseline"]
    pbp=preparation["padded-baseline"]/count["padded-baseline"]
    printf "padded_evaluation_speedup\t%d\t%d\t0\t%.9f\t%.9f\n",count["exact-baseline"],accepted["padded-baseline"],eb/pb,(ebp+eb)/(pbp+pb)
    printf "exact_profile_overhead\t%d\t%d\t0\t%.9f\t0\n",count["exact-profiled"],accepted["exact-profiled"],ep/eb
    printf "padded_profile_overhead\t%d\t%d\t0\t%.9f\t0\n",count["padded-profiled"],accepted["padded-profiled"],pp/pb
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk '
  function value(name, i, field) {
    for (i=1; i<=NF; ++i) {
      split($i, field, "="); if (field[1] == name) return field[2]
    }
  }
  /^CANDLE_NL_NATIVE_FIXED_SCALE_HISTORICAL_PROFILE / {
    representation=(FILENAME ~ /exact-profiled/) ? "exact" : "padded"
    idx=value("index"); key=representation SUBSEP idx
    label[key]=value("label"); runs[key]++
    observations[key]+=value("observations")
    nanoseconds[key]+=value("nanoseconds")
  }
  END {
    print "index\tlabel\texact_mean_observations\texact_mean_nanoseconds\tpadded_mean_observations\tpadded_mean_nanoseconds\texact_over_padded_ratio"
    for (idx=0; idx<15; ++idx) {
      exact="exact" SUBSEP idx; padded="padded" SUBSEP idx
      exact_ns=nanoseconds[exact]/runs[exact]
      padded_ns=nanoseconds[padded]/runs[padded]
      ratio=(padded_ns == 0) ? 0 : exact_ns/padded_ns
      printf "%d\t%s\t%.3f\t%.3f\t%.3f\t%.3f\t%.9f\n", \
        idx,label[exact],observations[exact]/runs[exact],exact_ns, \
        observations[padded]/runs[padded],padded_ns,ratio
    }
  }
' "$output_dir"/repetition-*-exact-profiled.txt \
  "$output_dir"/repetition-*-padded-profiled.txt \
  >"$output_dir/representation-stage-ratios.tsv"

awk -v begin="$build_begin" -v exact="$build_exact_end" \
  -v padded="$build_padded_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_exact\t%.9f\n",(exact-begin)/1000000000
  printf "build_padded\t%.9f\n",(padded-exact)/1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/source-revision.txt" "$output_dir/summaries.txt" \
  "$output_dir"/repetition-*.txt "$output_dir"/*-bounds.txt \
  "$output_dir/padded-vs-exact-bounds.json" \
  "$output_dir/phase-times.tsv" \
  "$output_dir/representation-stage-ratios.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/evidence.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_HISTORICAL_REPRESENTATION_STAGES_OK DEVELOPMENT_NON_RELEASE'
