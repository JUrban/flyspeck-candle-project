#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 6 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv EXPECTED.tsv BOXES.tsv OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
expected=$3
boxes=$4
output_dir=$5
repetitions=$6
archive="$repo_root/docs/advice/Candle_NL_native_comparison_2026-10-06.zip"
specialized_driver="$repo_root/tools/nl_native_certificate_boxes.cc"
fixed_driver="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
analyzer="$repo_root/scripts/analyze-nl-native-stage-factorial.py"

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$boxes" ]]
[[ -f "$archive" && -f "$specialized_driver" && -f "$fixed_driver" ]]
[[ -x "$analyzer" ]]
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]
[[ $(wc -l <"$boxes") -eq 4173 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

head -n 16 "$jobs" >"$output_dir/jobs-prefix16.tsv"
head -n 16 "$expected" >"$output_dir/expected-prefix16.tsv"

unzip -q "$archive" -d "$output_dir"
audit_dir="$output_dir/Candle_NL_native_comparison"
(
  cd "$audit_dir"
  python3 reproduce.py
) >"$output_dir/audit-reproduction.log" 2>&1
build_dir="$audit_dir/build"

g++ -std=gnu++11 -frounding-math -ffp-contract=off -include cstring \
  -Wno-write-strings -O0 -I"$build_dir" "$specialized_driver" \
  "$build_dir/error.o" "$build_dir/interval.o" \
  "$build_dir/lineInterval.o" "$build_dir/secondDerive.o" \
  "$build_dir/univariate.o" "$build_dir/wide.o" \
  "$build_dir/taylorData.o" "$build_dir/Lib.o" "$build_dir/recurse.o" \
  -lm -lgmpxx -lgmp -o "$output_dir/certificate-box-benchmark"
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 "$fixed_driver" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-int128"

for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  /usr/bin/time -f 'elapsed_seconds=%e peak_rss_kb=%M' \
    -o "$output_dir/specialized-time-$repetition.txt" \
    "$output_dir/certificate-box-benchmark" "$boxes" \
    --direct-specialized \
    >"$output_dir/specialized-results-$repetition.txt" \
    2>"$output_dir/specialized-stderr-$repetition.txt"
done
"$output_dir/certificate-box-benchmark" "$boxes" 16 \
  --direct-specialized --full-diagnostics \
  >"$output_dir/specialized-stage-prefix16.txt" \
  2>"$output_dir/specialized-stage-prefix16-stderr.txt"
"$output_dir/certificate-box-benchmark" "$boxes" --direct-profile \
  >"$output_dir/direct-profile.txt" \
  2>"$output_dir/direct-profile-stderr.txt"

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
  --full-stage-diagnostics
)
"$output_dir/nl-native-int128" "$program" \
  "$output_dir/jobs-prefix16.tsv" "$output_dir/expected-prefix16.tsv" \
  "${common_options[@]}" >"$output_dir/generic-stage-prefix16.txt" \
  2>"$output_dir/generic-stage-prefix16-stderr.txt"
"$output_dir/nl-native-int128" "$program" \
  "$output_dir/jobs-prefix16.tsv" "$output_dir/expected-prefix16.tsv" \
  "${common_options[@]}" --historical-dihedral --historical-block-rounding \
  --historical-center-tangent \
  >"$output_dir/historical-stage-prefix16.txt" \
  2>"$output_dir/historical-stage-prefix16-stderr.txt"

rg 'CANDLE_NL_NATIVE_BOX_SUMMARY' \
  "$output_dir"/specialized-results-*.txt >"$output_dir/summaries.txt"
awk '
  /CANDLE_NL_NATIVE_BOX_SUMMARY/ {
    mode = ""; preparation = wall = domain = evalf = upper = 0; accepted = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "mode") mode = field[2];
      else if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      else if (field[1] == "wall_seconds") wall = field[2] + 0;
      else if (field[1] == "domain_seconds") domain = field[2] + 0;
      else if (field[1] == "evalf_seconds") evalf = field[2] + 0;
      else if (field[1] == "upper_bound_seconds") upper = field[2] + 0;
      else if (field[1] == "accepted") accepted = field[2] + 0;
    }
    count[mode] += 1; preparation_sum[mode] += preparation;
    wall_sum[mode] += wall; domain_sum[mode] += domain;
    evalf_sum[mode] += evalf; upper_sum[mode] += upper;
    if (count[mode] == 1 || accepted < minimum_accepted[mode]) {
      minimum_accepted[mode] = accepted;
    }
  }
  END {
    print "mode\trepetitions\tmean_preparation_seconds\tmean_wall_seconds\tmean_domain_seconds\tmean_evalf_seconds\tmean_upper_bound_seconds\tminimum_accepted";
    for (mode_index = 1; mode_index <= 3; ++mode_index) {
      mode = mode_index == 1 ? "specialized" : mode_index == 2 ? "generic" : "direct-specialized";
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f\t%d\n", mode, count[mode], preparation_sum[mode] / count[mode], wall_sum[mode] / count[mode], domain_sum[mode] / count[mode], evalf_sum[mode] / count[mode], upper_sum[mode] / count[mode], minimum_accepted[mode];
    }
  }
' "$output_dir/summaries.txt" >"$output_dir/phase-times.tsv"

"$analyzer" "$output_dir/specialized-stage-prefix16.txt" \
  "$output_dir/generic-stage-prefix16.txt" \
  "$output_dir/historical-stage-prefix16.txt" \
  "$output_dir/specialized-stage-prefix16.txt" \
  >"$output_dir/stage-comparison.json"

rg -q "specialized[[:space:]]+$repetitions.*4173$" \
  "$output_dir/phase-times.tsv"
rg -q "generic[[:space:]]+$repetitions.*52$" \
  "$output_dir/phase-times.tsv"
rg -q "direct-specialized[[:space:]]+$repetitions.*4173$" \
  "$output_dir/phase-times.tsv"
rg -q 'CANDLE_NL_NATIVE_DIRECT_COMPARE boxes=4173' \
  "$output_dir/specialized-results-1.txt"
rg -q 'CANDLE_NL_NATIVE_DIRECT_PROFILE observations=4173' \
  "$output_dir/direct-profile.txt"
rg -q 'accepted=16' "$output_dir/generic-stage-prefix16.txt"
rg -q 'accepted=16' "$output_dir/historical-stage-prefix16.txt"

sha256sum "$archive" "$specialized_driver" "$fixed_driver" "$analyzer" \
  "$program" "$jobs" "$expected" "$boxes" \
  "$output_dir/jobs-prefix16.tsv" "$output_dir/expected-prefix16.tsv" \
  "$output_dir/certificate-box-benchmark" "$output_dir/nl-native-int128" \
  "$output_dir"/specialized-results-*.txt \
  "$output_dir"/specialized-stderr-*.txt \
  "$output_dir"/specialized-time-*.txt \
  "$output_dir/specialized-stage-prefix16.txt" \
  "$output_dir/specialized-stage-prefix16-stderr.txt" \
  "$output_dir/direct-profile.txt" \
  "$output_dir/direct-profile-stderr.txt" \
  "$output_dir/generic-stage-prefix16.txt" \
  "$output_dir/generic-stage-prefix16-stderr.txt" \
  "$output_dir/historical-stage-prefix16.txt" \
  "$output_dir/historical-stage-prefix16-stderr.txt" \
  "$output_dir/summaries.txt" "$output_dir/phase-times.tsv" \
  "$output_dir/stage-comparison.json" >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_STAGE_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
