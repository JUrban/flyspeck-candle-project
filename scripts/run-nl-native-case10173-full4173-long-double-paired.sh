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

options=(
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
  "$output_dir/nl-native-$lane" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

run_lane int128 warmup
run_lane long-double warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane int128 "$repetition"
    run_lane long-double "$repetition"
  else
    run_lane long-double "$repetition"
    run_lane int128 "$repetition"
  fi
done

for lane in int128 long-double; do
  "$output_dir/nl-native-$lane" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
  rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
done

"$bound_analyzer" \
  "$output_dir/int128-results.txt" \
  "$output_dir/long-double-results.txt" \
  >"$output_dir/bound-containment.json"
python3 - "$output_dir/bound-containment.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    result = json.load(source)
if result["cells"] != 4173 or result["candidate_tighter"] != 0:
    raise SystemExit("long-double bounds do not contain the exact int128 bounds")
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
    ip = preparation_sum["int128"] / count["int128"];
    ie = evaluation_sum["int128"] / count["int128"];
    lp = preparation_sum["long-double"] / count["long-double"];
    le = evaluation_sum["long-double"] / count["long-double"];
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    printf "int128\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["int128"], ip, ie, ip + ie, minimum_accepted["int128"];
    printf "long_double_padded\t%d\t%.9f\t%.9f\t%.9f\t%d\n", count["long-double"], lp, le, lp + le, minimum_accepted["long-double"];
    printf "int128_over_long_double_evaluation\t%d\t0\t%.9f\t0\t%d\n", count["long-double"], ie / le, minimum_accepted["long-double"];
    printf "int128_over_long_double_batch\t%d\t0\t0\t%.9f\t%d\n", count["long-double"], (ip + ie) / (lp + le), minimum_accepted["long-double"];
    printf "long_double_over_historical_specialized_evaluation\t%d\t0\t%.9f\t0\t%d\n", count["long-double"], le / historical, minimum_accepted["long-double"];
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
  "$summaries" "$output_dir/int128-results.txt" \
  "$output_dir/long-double-results.txt" "$output_dir/int128-bounds.txt" \
  "$output_dir/long-double-bounds.txt" \
  "$output_dir/bound-containment.json" "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_FULL4173_LONG_DOUBLE_PAIRED_OK DEVELOPMENT_NON_RELEASE'
