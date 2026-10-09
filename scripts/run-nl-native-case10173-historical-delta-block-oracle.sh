#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv EXPECTED.tsv OUTPUT-DIR\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
expected=$3
output_dir=$4
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
source_revision=${CANDLE_NL_NATIVE_SOURCE_REVISION:-HEAD}
source_path=tools/nl_native_fixed_scale_case10173.cc

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

common_compile=(
  -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include"
)
build_begin=$(date +%s%N)
g++ "${common_compile[@]}" -DCANDLE_NL_CHECKED_INT192=1 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native-checked192"
build_checked_end=$(date +%s%N)
g++ "${common_compile[@]}" "$source_file" -lgmpxx -lgmp \
  -o "$output_dir/nl-native-mpz"
build_mpz_end=$(date +%s%N)

common_options=(
  --binary-scale-bits=40
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --source-dag-cache
  --computed-tight-sqrt-certificates
  --taylor-reconstructed-box
  --whole-box-jet
  --sign-specialized-interval-products
  --allow-rejected-development
  --count-fixed-quotients
  --historical-dihedral
  --historical-block-rounding
  --historical-center-tangent
  --historical-delta-block-diagnostics
)

run_lane() {
  local lane=$1
  shift
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M exit=%x' \
    -o "$output_dir/$lane-resource.txt" \
    "$output_dir/nl-native-$lane" "$program" "$jobs" "$expected" \
    "${common_options[@]}" "$@" >"$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_HISTORICAL_DELTA_BLOCK ' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-delta-blocks.tsv"
  rg '^CANDLE_NL_NATIVE_HISTORICAL_DELTA_BLOCK_SUMMARY ' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-summary.txt"
  [[ $(wc -l <"$output_dir/$lane-delta-blocks.tsv") -eq 4173 ]]
  awk '
    { if ($2 != "index=" (NR-1)) exit 1 }
    END { if (NR != 4173) exit 1 }
  ' "$output_dir/$lane-delta-blocks.tsv"
  rg -q 'cells=4173 .*interval_products=58422 endpoint_products=116844 ' \
    "$output_dir/$lane-summary.txt"
}

run_lane checked192 --dyadic-shift-fixed-quotient
run_lane mpz
cmp "$output_dir/checked192-delta-blocks.tsv" \
  "$output_dir/mpz-delta-blocks.tsv"

head -n 128 "$output_dir/checked192-delta-blocks.tsv" \
  >"$output_dir/prefix128-delta-blocks.tsv"
awk -v begin="$build_begin" -v checked="$build_checked_end" \
  -v mpz="$build_mpz_end" \
  'BEGIN { print "phase\tseconds"; \
    printf "build_checked192\t%.9f\n", (checked-begin)/1e9; \
    printf "build_mpz\t%.9f\n", (mpz-checked)/1e9 }' \
  >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/source-revision.txt" \
  "$output_dir/checked192-delta-blocks.tsv" \
  "$output_dir/mpz-delta-blocks.tsv" \
  "$output_dir/prefix128-delta-blocks.tsv" \
  "$output_dir/checked192-summary.txt" "$output_dir/mpz-summary.txt" \
  "$output_dir/checked192-resource.txt" "$output_dir/mpz-resource.txt" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/evidence.sha256"

sha256sum "$output_dir/prefix128-delta-blocks.tsv"
cat "$output_dir/checked192-summary.txt"
cat "$output_dir/checked192-resource.txt"
cat "$output_dir/mpz-resource.txt"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_HISTORICAL_DELTA_BLOCK_ORACLE_OK DEVELOPMENT_NON_RELEASE'
