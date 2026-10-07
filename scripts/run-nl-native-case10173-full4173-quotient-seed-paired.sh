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
payload_verifier="$repo_root/scripts/verify-nl-case10173-angle-payloads.py"
historical_specialized_seconds=0.082490265

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-int128"
build_end=$(date +%s%N)

common_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --decimal-scale=10000000
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
  --precompute-tight-sqrt-certificates
)

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local lane=$1
  local repetition=$2
  local options=("${common_options[@]}")
  if [[ "$lane" == hardware-seeded ]]; then
    options+=(--hardware-seeded-fixed-quotient)
  fi
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

run_lane integer-division warmup
run_lane hardware-seeded warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane integer-division "$repetition"
    run_lane hardware-seeded "$repetition"
  else
    run_lane hardware-seeded "$repetition"
    run_lane integer-division "$repetition"
  fi
done

for lane in integer-division hardware-seeded; do
  options=("${common_options[@]}")
  if [[ "$lane" == hardware-seeded ]]; then
    options+=(--hardware-seeded-fixed-quotient)
  fi
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
  rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
done
cmp "$output_dir/integer-division-bounds.txt" \
  "$output_dir/hardware-seeded-bounds.txt"

awk -v historical="$historical_specialized_seconds" '
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
    ip = preparation_sum["integer-division"] / count["integer-division"];
    ie = evaluation_sum["integer-division"] / count["integer-division"];
    hp = preparation_sum["hardware-seeded"] / count["hardware-seeded"];
    he = evaluation_sum["hardware-seeded"] / count["hardware-seeded"];
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    printf "integer_division\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["integer-division"], ip, ie, ip + ie, minimum_accepted["integer-division"];
    printf "hardware_seeded_exact_corrected\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["hardware-seeded"], hp, he, hp + he, minimum_accepted["hardware-seeded"];
    printf "integer_over_seeded_evaluation\t%d\t0\t%.9f\t0\t%d\n", count["hardware-seeded"], ie / he, minimum_accepted["hardware-seeded"];
    printf "integer_over_seeded_batch\t%d\t0\t0\t%.9f\t%d\n", count["hardware-seeded"], (ip + ie) / (hp + he), minimum_accepted["hardware-seeded"];
    printf "seeded_over_historical_specialized_evaluation\t%d\t0\t%.9f\t0\t%d\n", count["hardware-seeded"], he / historical, minimum_accepted["hardware-seeded"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$source_file" "$payload_verifier" "$program" "$jobs" \
  "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$summaries" \
  "$output_dir/integer-division-results.txt" \
  "$output_dir/hardware-seeded-results.txt" \
  "$output_dir/integer-division-bounds.txt" \
  "$output_dir/hardware-seeded-bounds.txt" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_FULL4173_QUOTIENT_SEED_PAIRED_OK DEVELOPMENT_NON_RELEASE'
