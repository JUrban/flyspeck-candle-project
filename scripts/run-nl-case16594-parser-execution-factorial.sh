#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  printf 'usage: %s PARSER CHECKER PAYLOAD OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

parser=$1
checker=$2
payload=$3
output_dir=$4
repetitions=$5

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
for input in "$parser" "$checker" "$payload"; do
  [[ -f "$input" ]]
done
[[ -x "$parser" ]]
[[ -x "$checker" ]]
[[ ! -e "$output_dir" ]]

expected_parser_sha=9b99322245123062c52e89173e4010125c9158d0cf8d92b27a43fd535198ac55
expected_checker_sha=2d9edf0b7016cfcdda93fb2ecc5139f4bdfc7c663e1545bde340a4daf91f8552
expected_payload_sha=18f425bec54821d7484c45310eb74a2399d04b6f62bbf81c5a06575e3d5c348a

actual_parser_sha=$(sha256sum "$parser" | awk '{print $1}')
actual_checker_sha=$(sha256sum "$checker" | awk '{print $1}')
actual_payload_sha=$(sha256sum "$payload" | awk '{print $1}')
[[ "$actual_parser_sha" == "$expected_parser_sha" ]]
[[ "$actual_checker_sha" == "$expected_checker_sha" ]]
[[ "$actual_payload_sha" == "$expected_payload_sha" ]]
[[ $(wc -c <"$payload") -eq 2705516 ]]

mkdir -p "$output_dir"
timings="$output_dir/runs.tsv"
printf 'lane\trepetition\twall_seconds\tuser_seconds\tsystem_seconds\tmaximum_rss_kib\texit\n' >"$timings"

run_lane() {
  local lane=$1 repetition=$2 executable=$3 destination=$4
  local time_file="$output_dir/.time-$lane-$repetition.txt"
  /usr/bin/time \
    -f "$lane\t$repetition\t%e\t%U\t%S\t%M\t%x" \
    -o "$time_file" \
    env CML_HEAP_SIZE=1024 "$executable" <"$payload" >"$destination"
  [[ $(cat "$destination") == accepted ]]
  if [[ "$repetition" != warmup ]]; then
    sed -n '1p' "$time_file" >>"$timings"
  fi
  rm "$time_file"
}

run_lane parser warmup "$parser" "$output_dir/parser-warmup.txt"
run_lane checker warmup "$checker" "$output_dir/checker-warmup.txt"

lanes=(parser checker)
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    if [[ "$lane" == parser ]]; then executable=$parser; else executable=$checker; fi
    run_lane "$lane" "$repetition" "$executable" \
      "$output_dir/$lane-run-$repetition.txt"
  done
done

awk -F '\t' '
  NR == 1 { next }
  {
    count[$1]++
    wall[$1] += $3
    user[$1] += $4
    system_time[$1] += $5
    if ($6 > peak[$1]) peak[$1] = $6
  }
  END {
    print "lane\truns\tmean_wall_seconds\tmean_user_seconds\tmean_system_seconds\tpeak_rss_kib"
    names[1] = "parser"; names[2] = "checker"
    for (i = 1; i <= 2; ++i) {
      lane = names[i]
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane], \
        wall[lane] / count[lane], user[lane] / count[lane], \
        system_time[lane] / count[lane], peak[lane]
    }
  }
' "$timings" >"$output_dir/summary.tsv"

awk -F '\t' '
  NR == 2 { parser = $3 }
  NR == 3 { checker = $3 }
  END {
    printf "parser_fraction_of_checker\t%.9f\n", parser / checker
    printf "checker_over_parser\t%.9f\n", checker / parser
  }
' "$output_dir/summary.tsv" >"$output_dir/ratios.tsv"

sha256sum "$0" "$parser" "$checker" "$payload" \
  "$output_dir/runs.tsv" "$output_dir/summary.tsv" \
  "$output_dir/ratios.tsv" >"$output_dir/evidence.sha256"

cat "$output_dir/summary.tsv"
cat "$output_dir/ratios.tsv"
printf '%s\n' \
  'CANDLE_NL_CASE16594_PARSER_EXECUTION_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
