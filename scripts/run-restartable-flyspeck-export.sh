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
checkpoint_files_per_generation=${CANDLE_PFT_CHECKPOINT_FILES:-10}
max_generations=${CANDLE_PFT_MAX_GENERATIONS:-1000}
active_port=

case "$output$state_dir" in
  *$'\n'*|*$'\t'*|*'"'*|*'\\'*)
    printf 'paths may not contain tabs, newlines, quotes, or backslashes\n' >&2
    exit 2;;
esac
[[ "$checkpoint_files_per_generation" =~ ^[1-9][0-9]*$ ]]
[[ "$max_generations" =~ ^[1-9][0-9]*$ ]]

for command in dmtcp_coordinator dmtcp_launch dmtcp_command dmtcp_restart \
               truncate timeout python3 rg realpath git; do
  command -v "$command" >/dev/null
done

producer_head=$(git -C "$producer_dir" rev-parse HEAD)
flyspeck_head=$(git -C "$flyspeck_dir" rev-parse HEAD)
candle_head=$(git -C "$candle_dir" rev-parse HEAD)

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
    printf 'schema=1\n'
    printf 'sequence=%s\n' "$sequence"
    printf 'output=%s\n' "$output"
    printf 'producer_head=%s\n' "$producer_head"
    printf 'flyspeck_head=%s\n' "$flyspeck_head"
    printf 'candle_head=%s\n' "$candle_head"
    printf 'checkpoint_files=%s\n' "$checkpoint_files_per_generation"
  } >"$config_file"
  fresh_run=1
else
  [[ -f "$config_file" && -d "$checkpoint_dir" && -d "$log_dir" ]] || {
    printf 'invalid state directory: %s\n' "$state_dir" >&2
    exit 2
  }
  [[ $(read_config_value schema) == 1 ]]
  [[ $(read_config_value sequence) == "$sequence" ]]
  [[ $(read_config_value output) == "$output" ]]
  [[ $(read_config_value producer_head) == "$producer_head" ]]
  [[ $(read_config_value flyspeck_head) == "$flyspeck_head" ]]
  [[ $(read_config_value candle_head) == "$candle_head" ]]
  [[ $(read_config_value checkpoint_files) == \
     "$checkpoint_files_per_generation" ]]
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
  "OCAMLPATH=$ocaml_switch/lib"
  "CAML_LD_LIBRARY_PATH=$ocaml_switch/lib/stublibs:/usr/lib/ocaml/stublibs"
  "HOLLIGHT_DIR=$producer_dir"
  "FLYSPECK_DIR=$flyspeck_dir/text_formalization"
  "CANDLE_PFT_OUTPUT=$output"
  "CANDLE_PFT_CHECKPOINT_STATUS=$status_file"
  "CANDLE_FLYSPECK_SEQUENCE=$sequence"
  "CANDLE_PFT_PROCESS_CHECKPOINTS=1"
  "CANDLE_PFT_CHECKPOINT_FILES=$checkpoint_files_per_generation"
  "CANDLE_PFT_RESUME_SCRIPT=$export_script"
)

run_initial_generation() {
  local port_file="$state_dir/initial.port"
  dmtcp_coordinator --daemon --coord-port 0 --port-file "$port_file" \
    --ckptdir "$checkpoint_dir" \
    --coord-logfile "$log_dir/coordinator-initial.log" >/dev/null
  for _ in 1 2 3 4 5; do
    [[ -s "$port_file" ]] && break
    sleep 1
  done
  active_port=$(tr -d '[:space:]' <"$port_file")
  [[ "$active_port" =~ ^[0-9]+$ ]]
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
  timeout 86400 dmtcp_restart --new-coordinator --coord-port 0 \
    --ckptdir "$checkpoint_dir" "$checkpoint" \
    >"$log_dir/generation-$(printf '%04d' "$generation").log" 2>&1
}

if [[ $fresh_run == 1 ]]; then
  run_initial_generation
fi

complete=0
for ((generation = 1; generation <= max_generations; generation++)); do
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
  run_restart_generation "$generation" "$checkpoint"
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
  expected_target=flyspeck\$The_main_statement.kepler_conjecture_with_assumptions
  if [[ "$sequence" == full ]]; then
    expected_target=flyspeck\$The_kepler_conjecture.tame_nonlinear_imp_kepler_conjecture
  fi
  timeout 86400 "$candle_dir/candle.sh" >"$state_dir/replay.log" 2>&1 <<EOF
#use "candle/pft/replay.ml";;
allow_standard_pft_axioms ();;
let evidence = replay "$output";;
if map fst (pft_result_saved_theorems evidence) = ["$expected_target"] &&
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
