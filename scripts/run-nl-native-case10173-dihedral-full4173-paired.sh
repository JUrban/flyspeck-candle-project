#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  printf 'usage: %s PROGRAM.cval BOXES.tsv OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
boxes=$2
output_dir=$3
repetitions=$4
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
payload_verifier="$repo_root/scripts/verify-nl-case10173-angle-payloads.py"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$boxes" && -f "$source_file" ]]
[[ -x "$payload_verifier" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
placeholder='1:1,1:1,1:1,1:1,1:1,1:1,1:1'
generation_begin=$(date +%s%N)
awk -F '\t' -v OFS='\t' -v placeholder="$placeholder" '
  NF != 3 { exit 1 }
  $1 != rows { exit 1 }
  { print $1, placeholder, placeholder, $2, $3; ++rows }
  END { if (rows != 4173) exit 1 }
' "$boxes" >"$output_dir/jobs.tsv"
awk -F '\t' -v OFS='\t' '
  NF != 3 { exit 1 }
  $1 != rows { exit 1 }
  { print $1, 0; ++rows }
  END { if (rows != 4173) exit 1 }
' "$boxes" >"$output_dir/zero-expected.tsv"
generation_end=$(date +%s%N)

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_CHECKED_INT128=1 -I"$boost_include" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-checked128"
build_end=$(date +%s%N)

common_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --decimal-scale=10000000000
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
  --computed-tight-sqrt-certificates
)

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local lane=$1
  local repetition=$2
  local options=("${common_options[@]}")
  if [[ "$lane" == specialized ]]; then
    options+=(
      --specialized-dihedral-identities
      --optimized-dihedral-u-bounds
    )
  fi
  "$output_dir/nl-native-fixed-scale-checked128" \
    "$program" "$output_dir/jobs.tsv" "$output_dir/zero-expected.tsv" \
    "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

run_lane generic warmup
run_lane specialized warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane generic "$repetition"
    run_lane specialized "$repetition"
  else
    run_lane specialized "$repetition"
    run_lane generic "$repetition"
  fi
done

for lane in generic specialized; do
  options=("${common_options[@]}")
  if [[ "$lane" == specialized ]]; then
    options+=(
      --specialized-dihedral-identities
      --optimized-dihedral-u-bounds
    )
  fi
  "$output_dir/nl-native-fixed-scale-checked128" \
    "$program" "$output_dir/jobs.tsv" "$output_dir/zero-expected.tsv" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
done

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = 0; evaluation = 0; accepted = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    count[lane] += 1;
    if (count[lane] == 1 || accepted < minimum_accepted[lane]) {
      minimum_accepted[lane] = accepted;
    }
  }
  END {
    gp = preparation_sum["generic"] / count["generic"];
    ge = evaluation_sum["generic"] / count["generic"];
    sp = preparation_sum["specialized"] / count["specialized"];
    se = evaluation_sum["specialized"] / count["specialized"];
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    printf "generic\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["generic"], gp, ge, gp + ge, minimum_accepted["generic"];
    printf "specialized\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["specialized"], sp, se, sp + se, minimum_accepted["specialized"];
    printf "specialized_over_generic_evaluation\t%d\t0\t%.9f\t0\t%d\n", count["specialized"], se / ge, minimum_accepted["specialized"];
    printf "specialized_over_generic_batch\t%d\t0\t0\t%.9f\t%d\n", count["specialized"], (sp + se) / (gp + ge), minimum_accepted["specialized"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v generation_begin="$generation_begin" -v generation_end="$generation_end" \
    -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "external_job_generation\t%.9f\n", (generation_end - generation_begin) / 1000000000;
    printf "build\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$source_file" "$payload_verifier" "$program" "$boxes" \
  "$output_dir/payload-identities.txt" "$output_dir/jobs.tsv" \
  "$output_dir/zero-expected.tsv" \
  "$output_dir/nl-native-fixed-scale-checked128" "$summaries" \
  "$output_dir/generic-results.txt" "$output_dir/specialized-results.txt" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_DIHEDRAL_FULL4173_PAIRED_OK DEVELOPMENT_NON_RELEASE'
