#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 6 || $# -gt 7 ]]; then
  printf 'usage: %s CONTROL-BINARY CONTROL-ASSEMBLY DAG-BINARY PAYLOAD DAG-WORKTREE RUN-DIRECTORY [PAIRS]\n' "$0" >&2
  exit 2
fi

control_binary=$1
control_assembly=$2
dag_binary=$3
payload=$4
dag_worktree=$5
run_directory=$6
pairs=${7:-9}

expected_control_binary_sha=2d9edf0b7016cfcdda93fb2ecc5139f4bdfc7c663e1545bde340a4daf91f8552
expected_control_assembly_sha=97d96d2aa18eb61930a7775c40699dbbd65134a21c3ee9c1c54908ab26e03a3e
expected_payload_sha=18f425bec54821d7484c45310eb74a2399d04b6f62bbf81c5a06575e3d5c348a

[[ "$pairs" =~ ^[1-9][0-9]*$ ]]
[[ -x "$control_binary" && -x "$dag_binary" ]]
[[ -f "$control_assembly" && -f "$payload" ]]
[[ -d "$dag_worktree/.git" || -f "$dag_worktree/.git" ]]
[[ ! -e "$run_directory" ]]
[[ $(sha256sum "$control_binary" | awk '{print $1}') == "$expected_control_binary_sha" ]]
[[ $(sha256sum "$control_assembly" | awk '{print $1}') == "$expected_control_assembly_sha" ]]
[[ $(sha256sum "$payload" | awk '{print $1}') == "$expected_payload_sha" ]]
[[ $(wc -c <"$payload") -eq 2705516 ]]

compute_dir="$dag_worktree/candle/prover/compute"
sources=(
  "$compute_dir/compute_boundedCase16594SourceDagPlanScript.sml"
  "$compute_dir/compute_boundedCase16594SourceDagEvalScript.sml"
  "$compute_dir/compute_boundedPackedSourceDagCase16594CheckScript.sml"
  "$compute_dir/compute_boundedCase16594SourceDagEvalProgScript.sml"
  "$compute_dir/compute_boundedPackedSourceDagCase16594CheckProgScript.sml"
  "$compute_dir/compute_boundedPackedSourceDagCase16594CheckCompileScript.sml"
  "$compute_dir/compute_bounded_packed_source_dag_case16594_check.S"
)
for source in "${sources[@]}"; do
  [[ -f "$source" ]]
done

mkdir "$run_directory"
{
  printf 'status=DEVELOPMENT_NON_RELEASE_NON_AUTHORITATIVE\n'
  printf 'issued_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'pairs=%s\n' "$pairs"
  printf 'cells_per_run=875\n'
  printf 'payload_bytes=2705516\n'
  printf 'cml_heap_mib=1024\n'
  printf 'cml_stack_mib=1024\n'
  printf 'dag_git_head=%s\n' "$(git -C "$dag_worktree" rev-parse HEAD)"
  sha256sum "$0" "$control_binary" "$control_assembly" "$dag_binary" \
    "$payload" "${sources[@]}"
} >"$run_directory/manifest.txt"

printf 'pair\tposition\tlane\twall_seconds\tuser_seconds\tsystem_seconds\tmaximum_rss_kib\texit\n' \
  >"$run_directory/runs.tsv"
printf 'pair\tposition\tlane\twall_seconds\tuser_seconds\tsystem_seconds\tmaximum_rss_kib\texit\n' \
  >"$run_directory/warmups.tsv"

run_lane() {
  local pair=$1 position=$2 lane=$3 executable=$4
  local timing_file="$run_directory/.timing-$pair-$position-$lane"
  local output_file="$run_directory/$lane-$pair-$position.txt"
  /usr/bin/time -f '%e\t%U\t%S\t%M\t%x' -o "$timing_file" \
    env CML_HEAP_SIZE=1024 CML_STACK_SIZE=1024 "$executable" \
      <"$payload" >"$output_file"
  [[ $(sed -n '1p' "$output_file") == accepted ]]
  local ledger="$run_directory/runs.tsv"
  if [[ "$pair" == warmup ]]; then
    ledger="$run_directory/warmups.tsv"
  fi
  printf '%s\t%s\t%s\t' "$pair" "$position" "$lane" >>"$ledger"
  sed -n '1p' "$timing_file" >>"$ledger"
  rm "$timing_file"
}

run_lane warmup 1 control "$control_binary"
run_lane warmup 2 source_dag "$dag_binary"

for pair in $(seq 1 "$pairs"); do
  if (( pair % 2 == 1 )); then
    run_lane "$pair" 1 control "$control_binary"
    run_lane "$pair" 2 source_dag "$dag_binary"
  else
    run_lane "$pair" 1 source_dag "$dag_binary"
    run_lane "$pair" 2 control "$control_binary"
  fi
done

awk -F '\t' '
  NR > 1 {
    count[$3] += 1; wall[$3] += $4; user[$3] += $5;
    system_time[$3] += $6;
    if ($7 > peak[$3]) peak[$3] = $7;
    if ($8 != 0) bad[$3] += 1;
  }
  END {
    print "lane\truns\tmean_wall_seconds\tmean_user_seconds\tmean_system_seconds\tpeak_rss_kib\tnonzero_exits";
    names[1] = "control"; names[2] = "source_dag";
    for (i = 1; i <= 2; ++i) {
      lane = names[i];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\t%d\n", lane,
        count[lane], wall[lane] / count[lane], user[lane] / count[lane],
        system_time[lane] / count[lane], peak[lane], bad[lane] + 0;
    }
    control_mean = wall["control"] / count["control"];
    dag_mean = wall["source_dag"] / count["source_dag"];
    printf "control_over_source_dag_speedup\t%.9f\n", control_mean / dag_mean;
    printf "source_dag_time_reduction_fraction\t%.9f\n", 1 - dag_mean / control_mean;
  }
' "$run_directory/runs.tsv" >"$run_directory/summary.tsv"

sha256sum "$run_directory/manifest.txt" "$run_directory/warmups.tsv" \
  "$run_directory/runs.tsv" \
  "$run_directory/summary.tsv" "$run_directory"/*.txt \
  >"$run_directory/SHA256SUMS"
sha256sum -c "$run_directory/SHA256SUMS"
sed -n '1,8p' "$run_directory/summary.tsv"
printf '%s\n' 'CANDLE_NL_CASE16594_SOURCE_DAG_TRANSFER_GATE_OK DEVELOPMENT_NON_RELEASE'
