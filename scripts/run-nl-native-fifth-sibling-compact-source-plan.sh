#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  printf 'usage: %s PROGRAM.cval FULL-JOBS.tsv WHOLE-DECISIONS.txt OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
full_jobs=$2
whole_decisions=$3
output_dir=$4
repetitions=$5
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
source_revision=${CANDLE_NL_NATIVE_SOURCE_REVISION:-HEAD}
source_path=tools/nl_native_fixed_scale_case10173.cc

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
for input in "$program" "$full_jobs" "$whole_decisions"; do
  [[ -f "$input" ]]
done
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

resolved_revision=$(git -C "$repo_root" rev-parse "$source_revision^{commit}")
source_file="$output_dir/nl_native_fixed_scale_case10173.cc"
git -C "$repo_root" show "$resolved_revision:$source_path" >"$source_file"
printf 'revision=%s\nsource_path=%s\n' "$resolved_revision" "$source_path" \
  >"$output_dir/source-revision.txt"
rg -q -- '--whole-box-plan' "$source_file"
rg -q 'prepare_source_dag_plan' "$source_file"

jobs="$output_dir/whole-adaptive-jobs.tsv"
expected="$output_dir/whole-adaptive-zero-expected.tsv"
awk '
  NR == FNR {
    for (i = 1; i <= NF; ++i) {
      split($i,field,"=")
      if (field[1] == "node") wanted[field[2]] = 1
    }
    next
  }
  ($1 in wanted) { $1 = count++; print }
  END { if (count != 1302) exit 2 }
' OFS='\t' "$whole_decisions" "$full_jobs" >"$jobs"
awk 'BEGIN { for (i = 0; i < 1302; ++i) print i "\t0" }' >"$expected"

common=(-std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include")
defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)
build_begin=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_INT128=1 \
  -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 "${defines[@]}" \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-exact"
build_exact_end=$(date +%s%N)
g++ "${common[@]}" -DCANDLE_NL_FIXED_DOUBLE=1 "${defines[@]}" \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-padded"
build_padded_end=$(date +%s%N)

common_options=(
  --count-fixed-quotients
  --binary-scale-bits=40
  --sign-specialized-interval-products
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --taylor-reconstructed-box
  --specialized-delta-radicands
  --specialized-delta-derivatives
  --prepared-simple-polynomials
  --source-dag-cache
  --computed-tight-sqrt-certificates
  --allow-rejected-development
  --subdivide-domain-failures-development
  --specialized-delta-historical-dihedrals
)

run_lane() {
  local backend=$1 plan=$2 repetition=$3 destination=$4 binary
  local -a options=("${common_options[@]}")
  if [[ "$backend" == exact ]]; then
    binary="$output_dir/nl-native-exact"
    options+=(--dyadic-shift-fixed-quotient)
  else
    binary="$output_dir/nl-native-padded"
    options+=(--subdivide-representation-failures-development)
  fi
  if [[ "$plan" == compact ]]; then
    options+=(--whole-box-plan)
  else
    options+=(--whole-box-jet)
  fi
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY ' |
    sed "s/$/ backend_lane=$backend plan_lane=$plan repetition=$repetition/" \
      >>"$destination"
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
for backend in exact padded; do
  run_lane "$backend" sequential warmup /dev/null
  run_lane "$backend" compact warmup /dev/null
done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then plans=(sequential compact); else plans=(compact sequential); fi
  for backend in exact padded; do
    for plan in "${plans[@]}"; do
      run_lane "$backend" "$plan" "$repetition" "$summaries"
    done
  done
done

for backend in exact padded; do
  binary="$output_dir/nl-native-$backend"
  options=("${common_options[@]}")
  if [[ "$backend" == exact ]]; then
    options+=(--dyadic-shift-fixed-quotient)
  else
    options+=(--subdivide-representation-failures-development)
  fi
  for plan in sequential compact; do
    lane_options=("${options[@]}")
    if [[ "$plan" == compact ]]; then
      lane_options+=(--whole-box-plan)
    else
      lane_options+=(--whole-box-jet)
    fi
    /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
      -o "$output_dir/$backend-$plan-resource.txt" \
      "$binary" "$program" "$jobs" "$expected" "${lane_options[@]}" \
      >"$output_dir/$backend-$plan-results.txt"
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT ' \
      "$output_dir/$backend-$plan-results.txt" \
      >"$output_dir/$backend-$plan-bounds.txt"
  done
  cmp "$output_dir/$backend-sequential-bounds.txt" \
      "$output_dir/$backend-compact-bounds.txt"
done

awk '
  function value(name,i,field) {
    for (i=1;i<=NF;++i) {
      split($i,field,"="); if(field[1]==name)return field[2]
    }
  }
  {
    backend=value("backend_lane"); plan=value("plan_lane")
    key=backend "-" plan; count[key]++
    preparation[key]+=value("preparation_seconds")
    evaluation[key]+=value("evaluation_seconds")
  }
  END {
    print "backend\tplan\truns\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds"
    backends[1]="exact"; backends[2]="padded"
    plans[1]="sequential"; plans[2]="compact"
    for (b=1;b<=2;++b) for (p=1;p<=2;++p) {
      key=backends[b] "-" plans[p]
      prep=preparation[key]/count[key]; eval=evaluation[key]/count[key]
      printf "%s\t%s\t%d\t%.9f\t%.9f\t%.9f\n",backends[b],plans[p],count[key],prep,eval,prep+eval
    }
    for (b=1;b<=2;++b) {
      backend=backends[b]; sequential=backend "-sequential"; compact=backend "-compact"
      se=evaluation[sequential]/count[sequential]
      ce=evaluation[compact]/count[compact]
      st=(preparation[sequential]+evaluation[sequential])/count[sequential]
      ct=(preparation[compact]+evaluation[compact])/count[compact]
      printf "%s\tcompact_speedup\t%d\t0\t%.9f\t%.9f\n",backend,count[compact],se/ce,st/ct
    }
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v exact="$build_exact_end" \
  -v padded="$build_padded_end" 'BEGIN {
    print "phase\tseconds"
    printf "build_exact\t%.9f\n",(exact-begin)/1e9
    printf "build_padded\t%.9f\n",(padded-exact)/1e9
  }' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$full_jobs" \
  "$whole_decisions" "$jobs" "$expected" \
  "$output_dir/source-revision.txt" "$summaries" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir"/*-resource.txt >"$output_dir/evidence.sha256"

cat "$output_dir/phase-times.tsv"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIFTH_SIBLING_COMPACT_SOURCE_PLAN_OK DEVELOPMENT_NON_RELEASE'
