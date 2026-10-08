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
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$jobs" "$expected" "$source_file"; do
  [[ -f "$input" ]]
done
[[ -x "$analyzer" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

common=(-std=c++17 -O2 -Wall -Wextra -Werror)
defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)

build_begin=$(date +%s%N)
g++ "${common[@]}" -I"$boost_include" \
  -DCANDLE_NL_FIXED_INT128=1 -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 \
  "${defines[@]}" \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-exact"
build_exact_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_DOUBLE=1 "${defines[@]}" \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-padded"
build_padded_end=$(date +%s%N)

lane_options() {
  local lane=$1
  printf '%s\0' --accept-only --count-fixed-quotients \
    --binary-scale-bits=40 --sign-specialized-interval-products \
    --fixed-sqrt-inverse-kernels --fixed-atan-kernel \
    --taylor-reconstructed-box --specialized-delta-radicands \
    --specialized-delta-derivatives
  [[ "$lane" == exact-* ]] && \
    printf '%s\0' --dyadic-shift-fixed-quotient
  [[ "$lane" == *-identity ]] && \
    printf '%s\0' --specialized-delta-dihedral-identities
}

lane_binary() {
  local lane=$1
  if [[ "$lane" == exact-* ]]; then
    printf '%s\n' "$output_dir/nl-native-exact"
  else
    printf '%s\n' "$output_dir/nl-native-padded"
  fi
}

run_lane() {
  local lane=$1 repetition=$2 destination=$3 binary
  local -a options
  binary=$(lane_binary "$lane")
  mapfile -d '' -t options < <(lane_options "$lane")
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(exact-sequential exact-identity padded-sequential padded-identity)
summaries="$output_dir/summaries.txt"
: >"$summaries"
for lane in "${lanes[@]}"; do
  run_lane "$lane" warmup /dev/null
done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

for lane in "${lanes[@]}"; do
  binary=$(lane_binary "$lane")
  mapfile -d '' -t options < <(lane_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-resource.txt" \
    "$binary" "$program" "$jobs" "$expected" "${options[@]}" \
    >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-summary.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*fixed_sqrt_inverse_kernels=1 .*fixed_atan_kernel=1 .*accepted=875' \
    "$output_dir/$lane-summary.txt"
  if [[ "$lane" == *-identity ]]; then
    rg -q ' specialized_delta_dihedral_identities=1 specialized_delta_dihedral_chain_count=3 ' \
      "$output_dir/$lane-summary.txt"
  else
    rg -q ' specialized_delta_dihedral_identities=0 specialized_delta_dihedral_chain_count=0 ' \
      "$output_dir/$lane-summary.txt"
  fi
done

"$analyzer" "$output_dir/exact-sequential-results.txt" \
  "$output_dir/exact-identity-results.txt" \
  >"$output_dir/exact-identity-vs-sequential-bounds.json"
"$analyzer" "$output_dir/padded-sequential-results.txt" \
  "$output_dir/padded-identity-results.txt" \
  >"$output_dir/padded-identity-vs-sequential-bounds.json"
"$analyzer" "$output_dir/exact-sequential-results.txt" \
  "$output_dir/padded-sequential-results.txt" \
  >"$output_dir/padded-vs-exact-sequential-bounds.json"
"$analyzer" "$output_dir/exact-identity-results.txt" \
  "$output_dir/padded-identity-results.txt" \
  >"$output_dir/padded-vs-exact-identity-bounds.json"

awk '
  function value(name, i, field) {
    for (i = 1; i <= NF; ++i) {
      split($i, field, "="); if (field[1] == name) return field[2]
    }
  }
  {
    lane = value("lane"); if (lane == "") next
    count[lane]++
    preparation[lane] += value("preparation_seconds")
    evaluation[lane] += value("evaluation_seconds")
    accepted = value("accepted") + 0
    if (!(lane in minimum) || accepted < minimum[lane]) minimum[lane] = accepted
  }
  END {
    print "lane\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted"
    names[1]="exact-sequential"; names[2]="exact-identity"
    names[3]="padded-sequential"; names[4]="padded-identity"
    for (i = 1; i <= 4; ++i) {
      lane=names[i]
      p=preparation[lane]/count[lane]; e=evaluation[lane]/count[lane]
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n",lane,count[lane],p,e,p+e,minimum[lane]
    }
    xs=evaluation["exact-sequential"]/count["exact-sequential"]
    xi=evaluation["exact-identity"]/count["exact-identity"]
    ps=evaluation["padded-sequential"]/count["padded-sequential"]
    pi=evaluation["padded-identity"]/count["padded-identity"]
    xsp=preparation["exact-sequential"]/count["exact-sequential"]
    xip=preparation["exact-identity"]/count["exact-identity"]
    psp=preparation["padded-sequential"]/count["padded-sequential"]
    pip=preparation["padded-identity"]/count["padded-identity"]
    printf "exact_graph_speedup\t%d\t0\t%.9f\t0\t875\n",count["exact-sequential"],xs/xi
    printf "padded_graph_speedup\t%d\t0\t%.9f\t0\t875\n",count["padded-sequential"],ps/pi
    printf "sequential_arithmetic_speedup\t%d\t0\t%.9f\t0\t875\n",count["exact-sequential"],xs/ps
    printf "identity_arithmetic_speedup\t%d\t0\t%.9f\t0\t875\n",count["exact-identity"],xi/pi
    printf "exact_graph_batch_speedup\t%d\t0\t0\t%.9f\t875\n",count["exact-sequential"],(xsp+xs)/(xip+xi)
    printf "padded_graph_batch_speedup\t%d\t0\t0\t%.9f\t875\n",count["padded-sequential"],(psp+ps)/(pip+pi)
    printf "sequential_arithmetic_batch_speedup\t%d\t0\t0\t%.9f\t875\n",count["exact-sequential"],(xsp+xs)/(psp+ps)
    printf "identity_arithmetic_batch_speedup\t%d\t0\t0\t%.9f\t875\n",count["exact-identity"],(xip+xi)/(pip+pi)
    printf "graph_arithmetic_interaction\t%d\t0\t%.9f\t0\t875\n",count["exact-sequential"],(xs/xi)/(ps/pi)
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v exact="$build_exact_end" \
    -v padded="$build_padded_end" 'BEGIN {
  print "phase\tseconds"
  printf "build_exact\t%.9f\n",(exact-begin)/1000000000
  printf "build_padded\t%.9f\n",(padded-exact)/1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/summaries.txt" "$output_dir"/*-results.txt \
  "$output_dir"/*-bounds.txt "$output_dir"/*-summary.txt \
  "$output_dir"/*-bounds.json "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/evidence.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_DIHEDRAL_IDENTITY_ARITHMETIC_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
