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
bound_analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"
historical_specialized_seconds=0.082490265

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" && -x "$bound_analyzer" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-int128"
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_LONG_DOUBLE=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-long-double"
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
  local backend=int128
  local options=("${common_options[@]}")
  case "$lane" in
    generic-int)
      ;;
    historical-int)
      options+=(--historical-dihedral)
      ;;
    historical-block-int)
      options+=(--historical-dihedral --historical-block-rounding)
      ;;
    historical-block-long-double)
      backend=long-double
      options+=(--historical-dihedral --historical-block-rounding)
      ;;
    *)
      printf 'unknown lane: %s\n' "$lane" >&2
      exit 2
      ;;
  esac
  "$output_dir/nl-native-$backend" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

lanes=(generic-int historical-int historical-block-int historical-block-long-double)
for lane in "${lanes[@]}"; do
  run_lane "$lane" warmup
done
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition"
  done
done

for lane in "${lanes[@]}"; do
  backend=int128
  options=("${common_options[@]}")
  case "$lane" in
    generic-int)
      ;;
    historical-int)
      options+=(--historical-dihedral)
      ;;
    historical-block-int)
      options+=(--historical-dihedral --historical-block-rounding)
      ;;
    historical-block-long-double)
      backend=long-double
      options+=(--historical-dihedral --historical-block-rounding)
      ;;
  esac
  "$output_dir/nl-native-$backend" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
done

"$bound_analyzer" \
  "$output_dir/generic-int-results.txt" \
  "$output_dir/historical-block-int-results.txt" \
  >"$output_dir/historical-vs-generic-bounds.json"
"$bound_analyzer" \
  "$output_dir/historical-block-int-results.txt" \
  "$output_dir/historical-block-long-double-results.txt" \
  >"$output_dir/historical-long-double-containment.json"
python3 - "$output_dir/historical-long-double-containment.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    result = json.load(source)
if result["cells"] != 4173 or result["candidate_tighter"] != 0:
    raise SystemExit(
        "long-double historical bounds do not contain int128 historical bounds"
    )
PY

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
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    for (lane_index = 1; lane_index <= 4; ++lane_index) {
      lane = lane_index == 1 ? "generic-int" : lane_index == 2 ? "historical-int" : lane_index == 3 ? "historical-block-int" : "historical-block-long-double";
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane], p, e, p + e, minimum_accepted[lane];
    }
    ge = evaluation_sum["generic-int"] / count["generic-int"];
    he = evaluation_sum["historical-int"] / count["historical-int"];
    be = evaluation_sum["historical-block-int"] / count["historical-block-int"];
    le = evaluation_sum["historical-block-long-double"] / count["historical-block-long-double"];
    printf "historical_over_generic_evaluation\t%d\t0\t%.9f\t0\t%d\n", count["historical-int"], he / ge, minimum_accepted["historical-int"];
    printf "block_rounding_speedup\t%d\t0\t%.9f\t0\t%d\n", count["historical-block-int"], he / be, minimum_accepted["historical-block-int"];
    printf "int_over_long_double_historical_evaluation\t%d\t0\t%.9f\t0\t%d\n", count["historical-block-long-double"], be / le, minimum_accepted["historical-block-long-double"];
    printf "historical_block_over_cpp_specialized\t%d\t0\t%.9f\t0\t%d\n", count["historical-block-int"], be / historical, minimum_accepted["historical-block-int"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_two_backends\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$source_file" "$payload_verifier" "$bound_analyzer" \
  "$program" "$jobs" "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$output_dir/nl-native-long-double" \
  "$summaries" "$output_dir/generic-int-results.txt" \
  "$output_dir/historical-int-results.txt" \
  "$output_dir/historical-block-int-results.txt" \
  "$output_dir/historical-block-long-double-results.txt" \
  "$output_dir/historical-vs-generic-bounds.json" \
  "$output_dir/historical-long-double-containment.json" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_HISTORICAL_DIHEDRAL_PAIRED_OK DEVELOPMENT_NON_RELEASE'
