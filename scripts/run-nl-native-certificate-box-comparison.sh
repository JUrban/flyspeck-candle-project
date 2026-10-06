#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'usage: %s CASE10173-BOXES.tsv OUTPUT-DIR\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
boxes=$1
output_dir=$2
archive="$repo_root/docs/advice/Candle_NL_native_comparison_2026-10-06.zip"
driver="$repo_root/tools/nl_native_certificate_boxes.cc"

[[ -f "$boxes" ]]
[[ -f "$archive" ]]
[[ -f "$driver" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

unzip -q "$archive" -d "$output_dir"
audit_dir="$output_dir/Candle_NL_native_comparison"
(
  cd "$audit_dir"
  python3 reproduce.py
) >"$output_dir/audit-reproduction.log" 2>&1

build_dir="$audit_dir/build"
g++ -std=gnu++11 -frounding-math -ffp-contract=off -include cstring \
  -Wno-write-strings -O0 -I"$build_dir" "$driver" \
  "$build_dir/error.o" "$build_dir/interval.o" \
  "$build_dir/lineInterval.o" "$build_dir/secondDerive.o" \
  "$build_dir/univariate.o" "$build_dir/wide.o" \
  "$build_dir/taylorData.o" "$build_dir/Lib.o" "$build_dir/recurse.o" \
  -lm -lgmpxx -lgmp -o "$output_dir/certificate-box-benchmark"

/usr/bin/time -v -o "$output_dir/time.txt" \
  "$output_dir/certificate-box-benchmark" "$boxes" \
  >"$output_dir/results.txt" 2>"$output_dir/stderr.txt"

rg -Fq 'CANDLE_NL_NATIVE_CERTIFICATE_BOX_COMPARE_OK' \
  "$output_dir/results.txt"
sha256sum "$archive" "$driver" "$boxes" \
  "$output_dir/audit-reproduction.log" "$output_dir/certificate-box-benchmark" \
  "$output_dir/results.txt" "$output_dir/stderr.txt" "$output_dir/time.txt" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CERTIFICATE_BOX_COMPARE_DRIVER_OK DEVELOPMENT_NON_RELEASE'
