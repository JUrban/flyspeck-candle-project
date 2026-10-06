#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'usage: %s NATIVE-INPUT-RUN-DIR OUTPUT-DIR\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
input_dir=$1
output_dir=$2
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
program="$input_dir/case10173-program.cval"
jobs="$input_dir/case10173-native-jobs-prefix128.tsv"
expected=/project/flyspeck-candle-runs/cv-case10173-bound-tightness-prefix128-v3-16g-dev-001/case10173-reflected-bounds-prefix128.tsv

[[ -f "$source_file" ]]
[[ -f "$program" ]]
[[ -f "$jobs" ]]
[[ -f "$expected" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

g++ -std=c++17 -O2 -Wall -Wextra -Werror "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-case10173"

/usr/bin/time -v -o "$output_dir/time.txt" \
  "$output_dir/nl-native-fixed-scale-case10173" \
  "$program" "$jobs" "$expected" --profile \
  >"$output_dir/results.txt" 2>"$output_dir/stderr.txt"

rg -Fq 'CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_OK' "$output_dir/results.txt"
rg -Fq 'CANDLE_NL_NATIVE_FIXED_SCALE_PROFILE' "$output_dir/results.txt"
sha256sum "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/nl-native-fixed-scale-case10173" "$output_dir/results.txt" \
  "$output_dir/stderr.txt" "$output_dir/time.txt" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_PROFILE_DRIVER_OK DEVELOPMENT_NON_RELEASE'
