#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'usage: %s <main|full> <output.pft.bin> <state-directory>\n' "$0" >&2
  exit 2
}

[[ $# -eq 3 ]] || usage
sequence=$1
[[ "$sequence" == main || "$sequence" == full ]] || usage

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace_dir=$(cd -- "$project_dir/.." && pwd)
repos_dir="$workspace_dir/repos"
candle_dir="$repos_dir/candle"
flyspeck_dir="$repos_dir/flyspeck"
producer_dir="$repos_dir/hol-light-flyspeck"
ocaml_switch="$repos_dir/hol-light/_opam"
test_dir="$candle_dir/candle/pft/tests"
init_script="$test_dir/resume_smoke_init.ml"
export_script="$flyspeck_dir/text_formalization/candle/export_restartable_build.hl"
output=$(realpath -m -- "$2")
state_dir=$(realpath -m -- "$3")
status_file="$state_dir/status.tsv"
config_file="$state_dir/run.conf"
checkpoint_dir="$state_dir/checkpoints"
log_dir="$state_dir/logs"
active_port_file="$state_dir/coordinator.port"
checkpoint_files_per_generation=${CANDLE_PFT_CHECKPOINT_FILES:-10}
checkpoint_work_units_per_generation=${CANDLE_PFT_CHECKPOINT_WORK_UNITS:-25}
checkpoint_gzip=${CANDLE_PFT_DMTCP_GZIP:-0}
checkpoint_gzip_explicit=${CANDLE_PFT_DMTCP_GZIP+x}
max_generations=${CANDLE_PFT_MAX_GENERATIONS:-1000}
active_port=

case "$output$state_dir" in
  *$'\n'*|*$'\t'*|*'"'*|*'\\'*)
    printf 'paths may not contain tabs, newlines, quotes, or backslashes\n' >&2
    exit 2;;
esac
[[ "$checkpoint_files_per_generation" =~ ^[1-9][0-9]*$ ]]
[[ "$checkpoint_work_units_per_generation" =~ ^[1-9][0-9]*$ ]]
[[ "$checkpoint_gzip" =~ ^[01]$ ]]
[[ "$max_generations" =~ ^[1-9][0-9]*$ ]]

for command in dmtcp_coordinator dmtcp_launch dmtcp_command dmtcp_restart \
               truncate timeout python3 rg realpath git sha256sum xargs; do
  command -v "$command" >/dev/null
done

for repo in "$producer_dir" "$flyspeck_dir" "$candle_dir"; do
  git -C "$repo" diff --quiet
  git -C "$repo" diff --cached --quiet
done

producer_head=$(git -C "$producer_dir" rev-parse HEAD)
flyspeck_head=$(git -C "$flyspeck_dir" rev-parse HEAD)
candle_head=$(git -C "$candle_dir" rev-parse HEAD)
certificate_inventory_sha=$(
  cd "$flyspeck_dir/formal_lp/glpk/binary"
  find . -maxdepth 1 -type f \( -name 'easy*' -o -name 'hard*' \) -print0 |
    sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1
)
archive_sha=$(sha256sum \
  "$flyspeck_dir/formal_graph/archive/archive_all.ml" | cut -d' ' -f1)
nonlinear_prep_sha=$(sha256sum \
  "$flyspeck_dir/text_formalization/nonlinear/prep.hl" | cut -d' ' -f1)
nonlinear_log_sha=$(sha256sum \
  "$flyspeck_dir/text_formalization/nonlinear/break_case_log.hl" |
  cut -d' ' -f1)

read_config_value() {
  local key=$1
  sed -n "s/^${key}=//p" "$config_file"
}

if [[ ! -e "$state_dir" ]]; then
  [[ ! -e "$output" ]] || {
    printf 'refusing to overwrite output: %s\n' "$output" >&2
    exit 2
  }
  mkdir -p "$checkpoint_dir" "$log_dir" "$(dirname -- "$output")"
  {
    printf 'schema=2\n'
    printf 'sequence=%s\n' "$sequence"
    printf 'output=%s\n' "$output"
    printf 'producer_head=%s\n' "$producer_head"
    printf 'flyspeck_head=%s\n' "$flyspeck_head"
    printf 'candle_head=%s\n' "$candle_head"
    printf 'checkpoint_files=%s\n' "$checkpoint_files_per_generation"
    printf 'checkpoint_work_units=%s\n' \
      "$checkpoint_work_units_per_generation"
    printf 'checkpoint_gzip=%s\n' "$checkpoint_gzip"
    printf 'certificate_inventory_sha256=%s\n' "$certificate_inventory_sha"
    printf 'archive_sha256=%s\n' "$archive_sha"
    printf 'nonlinear_prep_sha256=%s\n' "$nonlinear_prep_sha"
    printf 'nonlinear_log_sha256=%s\n' "$nonlinear_log_sha"
  } >"$config_file"
  fresh_run=1
else
  [[ -f "$config_file" && -d "$checkpoint_dir" && -d "$log_dir" ]] || {
    printf 'invalid state directory: %s\n' "$state_dir" >&2
    exit 2
  }
  [[ $(read_config_value schema) == 2 ]]
  [[ $(read_config_value sequence) == "$sequence" ]]
  [[ $(read_config_value output) == "$output" ]]
  [[ $(read_config_value producer_head) == "$producer_head" ]]
  [[ $(read_config_value flyspeck_head) == "$flyspeck_head" ]]
  [[ $(read_config_value candle_head) == "$candle_head" ]]
  [[ $(read_config_value checkpoint_files) == \
     "$checkpoint_files_per_generation" ]]
  [[ $(read_config_value checkpoint_work_units) == \
     "$checkpoint_work_units_per_generation" ]]
  configured_checkpoint_gzip=$(read_config_value checkpoint_gzip)
  if [[ -z "$configured_checkpoint_gzip" ]]; then
    configured_checkpoint_gzip=1
  fi
  if [[ -z "$checkpoint_gzip_explicit" ]]; then
    checkpoint_gzip=$configured_checkpoint_gzip
  fi
  [[ "$configured_checkpoint_gzip" == "$checkpoint_gzip" ]]
  [[ $(read_config_value certificate_inventory_sha256) == \
     "$certificate_inventory_sha" ]]
  [[ $(read_config_value archive_sha256) == "$archive_sha" ]]
  [[ $(read_config_value nonlinear_prep_sha256) == "$nonlinear_prep_sha" ]]
  [[ $(read_config_value nonlinear_log_sha256) == "$nonlinear_log_sha" ]]
  fresh_run=0
  printf 'WARNING: restoring only locally created, trusted DMTCP images.\n' >&2
fi

cleanup_coordinator() {
  if [[ -n "$active_port" ]]; then
    DMTCP_COORD_PORT="$active_port" dmtcp_command -q >/dev/null 2>&1 || true
    active_port=
  fi
}
trap cleanup_coordinator EXIT

common_environment=(
  "PATH=$project_dir/scripts/bin:$PATH"
  "DMTCP_GZIP=$checkpoint_gzip"
  "OCAMLPATH=$ocaml_switch/lib"
  "CAML_LD_LIBRARY_PATH=$ocaml_switch/lib/stublibs:/usr/lib/ocaml/stublibs"
  "HOLLIGHT_DIR=$producer_dir"
  "FLYSPECK_DIR=$flyspeck_dir/text_formalization"
  "CANDLE_PFT_OUTPUT=$output"
  "CANDLE_PFT_CHECKPOINT_STATUS=$status_file"
  "CANDLE_FLYSPECK_SEQUENCE=$sequence"
  "CANDLE_PFT_PROCESS_CHECKPOINTS=1"
  "CANDLE_PFT_CHECKPOINT_FILES=$checkpoint_files_per_generation"
  "CANDLE_PFT_CHECKPOINT_WORK_UNITS=$checkpoint_work_units_per_generation"
  "CANDLE_PFT_RESUME_SCRIPT=$export_script"
)

run_initial_generation() {
  local port_file="$state_dir/initial.port"
  find "$port_file" -maxdepth 0 -type f -delete 2>/dev/null || true
  dmtcp_coordinator --daemon --coord-port 0 --port-file "$port_file" \
    --ckptdir "$checkpoint_dir" \
    --coord-logfile "$log_dir/coordinator-initial.log" >/dev/null
  for _ in 1 2 3 4 5; do
    [[ -s "$port_file" ]] && break
    sleep 1
  done
  active_port=$(tr -d '[:space:]' <"$port_file")
  [[ "$active_port" =~ ^[0-9]+$ ]]
  printf '%s\n' "$active_port" >"$active_port_file"
  (
    cd "$producer_dir"
    env "${common_environment[@]}" DMTCP_COORD_PORT="$active_port" \
      timeout 86400 dmtcp_launch --join-coordinator \
        --ckptdir "$checkpoint_dir" \
        ./ocaml-hol -init "$init_script" </dev/null \
        >"$log_dir/generation-0000.log" 2>&1
  )
  cleanup_coordinator
}

latest_checkpoint() {
  find "$checkpoint_dir" -maxdepth 1 -type f -name 'ckpt_*.dmtcp' \
    -printf '%T@\t%p\n' | sort -nr | head -n 1 | cut -f2-
}

run_restart_generation() {
  local generation=$1
  local checkpoint=$2
  local port_file="$state_dir/restart-$(printf '%04d' "$generation").port"
  local restart_pid
  local restart_status=0
  local wait_index
  find "$port_file" -maxdepth 0 -type f -delete 2>/dev/null || true
  (
    cd "$checkpoint_dir"
    env DMTCP_GZIP="$checkpoint_gzip" \
      timeout 86400 dmtcp_restart --new-coordinator --coord-port 0 \
        --port-file "$port_file" --ckptdir "$checkpoint_dir" "$checkpoint" \
        >"$log_dir/generation-$(printf '%04d' "$generation").log" 2>&1
  ) &
  restart_pid=$!
  for ((wait_index = 0; wait_index < 100; wait_index++)); do
    [[ -s "$port_file" ]] && break
    kill -0 "$restart_pid" 2>/dev/null || break
    sleep 0.1
  done
  if [[ ! -s "$port_file" ]]; then
    wait "$restart_pid" || true
    printf 'restart %d did not publish a coordinator port\n' \
      "$generation" >&2
    return 1
  fi
  active_port=$(tr -d '[:space:]' <"$port_file")
  [[ "$active_port" =~ ^[0-9]+$ ]]
  printf '%s\n' "$active_port" >"$active_port_file"
  wait "$restart_pid" || restart_status=$?
  cleanup_coordinator
  return "$restart_status"
}

if [[ $fresh_run == 1 ]]; then
  run_initial_generation
fi

first_generation=1
if [[ $fresh_run == 0 ]]; then
  latest_generation_log=$(
    find "$log_dir" -maxdepth 1 -type f -name 'generation-[0-9]*.log' \
      -printf '%f\n' | sort | tail -n 1
  )
  if [[ "$latest_generation_log" =~ ^generation-([0-9]+)\.log$ ]]; then
    first_generation=$((10#${BASH_REMATCH[1]} + 1))
  fi
fi

complete=0
for ((generation = first_generation;
      generation <= max_generations;
      generation++)); do
  phase=$(cut -f1 "$status_file" 2>/dev/null || true)
  if [[ "$phase" == complete ]]; then
    complete=1
    break
  fi
  [[ "$phase" == checkpoint || "$phase" == resumed ]] || {
    printf 'no restartable boundary in %s (phase %s)\n' \
      "$status_file" "$phase" >&2
    exit 1
  }
  checkpoint=$(latest_checkpoint)
  [[ -n "$checkpoint" && -f "$checkpoint" ]] || {
    printf 'missing checkpoint image for phase %s\n' "$phase" >&2
    exit 1
  }
  printf 'restart %d from %s\n' "$generation" "$(basename -- "$checkpoint")"
  if ! run_restart_generation "$generation" "$checkpoint"; then
    recovery_phase=$(cut -f1 "$status_file" 2>/dev/null || true)
    recovery_offset=$(cut -f4 "$status_file" 2>/dev/null || true)
    [[ "$recovery_phase" == checkpoint || "$recovery_phase" == resumed ]]
    [[ "$recovery_offset" =~ ^[0-9]+$ ]]
    output_size=$(stat -c '%s' "$output")
    if ((output_size < recovery_offset)); then
      printf 'failed generation %d left output shorter than boundary\n' \
        "$generation" >&2
      exit 1
    fi
    truncate -s "$recovery_offset" "$output"
    find "$checkpoint_dir" -maxdepth 1 -type f \
      -name 'ckpt_*.dmtcp.temp' -delete
    printf 'generation %d failed; restored output boundary %s for retry\n' \
      "$generation" "$recovery_offset" >&2
    continue
  fi
  next_phase=$(cut -f1 "$status_file" 2>/dev/null || true)
  next_checkpoint=$(latest_checkpoint)
  if [[ "$next_phase" == complete ||
        ( -n "$next_checkpoint" && "$next_checkpoint" != "$checkpoint" ) ]]; then
    find "$checkpoint" -maxdepth 0 -type f -delete
  fi
done
[[ $complete == 1 ]] || {
  printf 'generation limit reached without completion\n' >&2
  exit 1
}

python3 "$test_dir/inspect_opcodes.py" "$output" >"$state_dir/opcodes.json"
output_sha=$(sha256sum "$output" | cut -d' ' -f1)
printf '%s  %s\n' "$output_sha" "$(basename -- "$output")" \
  >"$state_dir/SHA256SUMS"

if [[ ${CANDLE_REPLAY_AFTER_EXPORT:-1} == 1 ]]; then
  expected_targets='["flyspeck$The_main_statement.kepler_conjecture_with_assumptions"]'
  if [[ "$sequence" == full ]]; then
    expected_targets='["flyspeck$Linear_programming_results.linear_programming_results_th"; "flyspeck$Mk_all_ineq.the_nonlinear_inequalities"; "flyspeck$The_kepler_conjecture.tame_nonlinear_imp_kepler_conjecture"; "flyspeck$Candle_flyspeck_l2.tame_imp_kepler_conjecture"]'
  fi
  timeout 86400 "$candle_dir/candle.sh" >"$state_dir/replay.log" 2>&1 <<EOF
#use "candle/pft/replay.ml";;
allow_standard_pft_axioms ();;
let evidence = replay "$output";;
if map fst (pft_result_saved_theorems evidence) = $expected_targets &&
   length (pft_result_axioms evidence) = 3
then print_endline "CANDLE_FULL_REPLAY_OK"
else failwith "unexpected restartable Flyspeck replay evidence";;
EOF
  rg -q '^Success!$' "$state_dir/replay.log"
  rg -q 'CANDLE_FULL_REPLAY_OK' "$state_dir/replay.log"
  if rg -q '^EXCEPTION:' "$state_dir/replay.log"; then
    tail -n 50 "$state_dir/replay.log" >&2
    exit 1
  fi
fi

if [[ ${CANDLE_KEEP_FINAL_CHECKPOINT:-0} != 1 ]]; then
  find "$checkpoint_dir" -maxdepth 1 -type f -name 'ckpt_*.dmtcp' -delete
  printf 'removed completed producer checkpoint images\n'
fi
printf 'complete: sequence=%s output=%s sha256=%s\n' \
  "$sequence" "$output" "$output_sha"
